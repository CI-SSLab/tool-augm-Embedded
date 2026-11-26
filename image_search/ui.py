import io
import json
import os
import re

from crewai import Crew, Process
from PIL import Image

from crew.agents.image_agent import build_image_agent
from crew.tasks.image_task import NO_MATCH_ANSWER, NO_MATCH_ANSWER_EN, build_image_task
from image_search.tool import get_last_image_trace, image_search
from ui_text import lang, t


def image_search_enabled() -> bool:
    return os.getenv("ENABLE_IMAGE_SEARCH", "").strip().lower() in ("1", "true", "yes")


# ----- TURN WITH AN IMAGE -----

def run_image_turn(question: str, photo: bytes, state) -> tuple:
    # Returns (raw LLM output, trace for the panel). state is st.session_state.
    # A new photo runs the image tool and becomes the "current object in thread";
    # a follow-up without photo reuses the stored result (records read by ID, no new search).
    if photo is not None:
        result = image_search(Image.open(io.BytesIO(photo)).convert("RGB"),
                              colour=os.getenv("IMAGE_COLOUR", "none"))
        state.current_object = {"result": result, "ranked": get_last_image_trace()["ranked"], "photo": photo}
    current = state.current_object
    trace = {"query": t("photo_query") if photo is not None else t("object_query"),
             "result": current["result"], "ranked": current["ranked"], "photo": current["photo"]}

    #Decided in code: without a record the LLM is not called
    if not json.loads(current["result"])["candidates"]:
        return f"<<<RISPOSTA>>>\n{NO_MATCH_ANSWER_EN if lang() == 'en' else NO_MATCH_ANSWER}\n<<<FINE>>>", trace

    agent = build_image_agent()
    crew = Crew(agents=[agent], tasks=[build_image_task(agent)], process=Process.sequential, verbose=False)
    result = crew.kickoff(inputs={"question": question, "tool_result": current["result"]})
    return with_sources(str(getattr(result, "raw", result)), current["result"]), trace


def with_sources(raw: str, result: str) -> str:
    #gpt-oss often drops the FONTI block: rebuild it in code from the records the tool returned
    match = re.search(r"<<<RISPOSTA>>>(.*?)<<<FINE>>>", raw, re.DOTALL | re.IGNORECASE)
    if not match:
        return raw
    text = re.split(r"\n\s*\**(?:FONTI|SOURCES)\**\s*:", match.group(1))[0].strip()
    urls = []
    for c in json.loads(result)["candidates"]:
        urls += [c["url"]] + ([c["site"]["url"]] if c.get("site") else [])
    label = "SOURCES" if lang() == "en" else "FONTI"
    return "<<<RISPOSTA>>>\n" + text + f"\n\n{label}:\n" + "\n".join(dict.fromkeys(urls)) + "\n<<<FINE>>>"


# ----- PANEL: TOP-K WITH SCORES -----

def render_image_tab(st, trace: dict):
    # Scores and thumbnails are shown only here, never passed to the LLM
    if trace.get("photo"):
        st.markdown(t("user_photo"))
        st.image(trace["photo"], width=240)
    decision = json.loads(trace["result"]).get("decision", "")
    st.markdown(f"{t('decision')} `{decision}`")
    cols = st.columns(max(len(trace["ranked"]), 1))
    for col, r in zip(cols, trace["ranked"]):
        col.image(r["image_url"], width="stretch")
        col.caption(f"{r['object_id']}\n\n{r['score']:.3f}")


if __name__ == "__main__":  # self-check of the sources rebuild
    res = json.dumps({"candidates": [{"url": "u1", "site": {"url": "s1"}}, {"url": "u2", "site": None}]})
    out = with_sources("x <<<RISPOSTA>>>testo\nFONTI: inventata<<<FINE>>>", res)
    assert out == "<<<RISPOSTA>>>\ntesto\n\nFONTI:\nu1\ns1\nu2\n<<<FINE>>>", out
    assert with_sources("no markers", res) == "no markers"
    print("ui.py self-check ok")
