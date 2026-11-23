"""Run the unmodified text-only agent on questions about the curated group.

Answers the question: before any extension, does the paper pipeline already
retrieve source records for these objects and sites?
Writes data/census/baseline_text_results.json and .csv (opera, domanda, risposta).

Usage: python eval/underwater/baseline_text.py [--csv-only]
"""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.update(OTEL_SDK_DISABLED="true", CREWAI_DISABLE_TELEMETRY="true", CREWAI_TRACING_ENABLED="false")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from crewai import Crew, Process  # noqa: E402

from crew.agents.qa_agent import build_qa_agent  # noqa: E402
from crew.tasks.answer_task import build_answer_task  # noqa: E402
from crew.tool.europeana_tool import get_last_tool_trace  # noqa: E402

# (object_id from curated_group.csv, question)
QUESTIONS = [
    ("baia_odysseus", "Parlami della statua di Ulisse del ninfeo di Baia"),
    ("baia_antonia", "Parlami della statua di Antonia del ninfeo di Baia"),
    ("site_punta_epitaffio", "Cos'è il Ninfeo di Punta Epitaffio?"),
    ("site_punta_epitaffio", "Cos'è il Parco sommerso di Baia?"),
    ("site_miseno_porto", "Cos'è il porto romano di Miseno?"),
    ("artemision_god", "Parlami dello Zeus di Capo Artemisio"),
    ("artemision_jockey", "Parlami del Fantino di Capo Artemisio"),
    ("antikythera_ephebe", "Parlami dell'Efebo di Anticitera"),
    ("antikythera_philosopher", "Parlami del Filosofo di Anticitera"),
]


def main():
    load_dotenv(ROOT / ".env")
    group = {r["object_id"]: r for r in csv.DictReader(open(ROOT / "data/census/curated_group.csv"))}
    results = []
    for obj_id, question in QUESTIONS:
        expected = set(filter(None, group[obj_id]["europeana_ids"].split(";")))
        agent = build_qa_agent()
        t = time.time()
        raw = str(Crew(agents=[agent], tasks=[build_answer_task(agent)], process=Process.sequential,
                       verbose=False).kickoff(inputs={"question": question, "current_artist": "(nessuno)"}).raw)
        trace = get_last_tool_trace()
        try:
            tool = json.loads(trace.get("result") or "{}")
        except json.JSONDecodeError:
            tool = {}
        items = tool.get("items", [])
        item_ids = {re.sub(r"^https://www\.europeana\.eu/it/item", "", it["url"]) for it in items}
        answer_urls = re.findall(r"https?://\S+", raw.split("FONTI:")[-1]) if "FONTI:" in raw else []
        row = {
            "object_id": obj_id, "question": question, "seconds": round(time.time() - t, 1),
            "tool_query": trace.get("query", ""), "tool_error": tool.get("error"),
            "n_items": len(items), "items": [f'{it["title"][:70]} | {it["creator"][:30]}' for it in items],
            "hits_curated_record": len(item_ids & expected), "answer_urls": len(answer_urls),
            "mentions_iccd": "beniculturali" in raw, "answer": raw,
        }
        results.append(row)
        print(f'{obj_id:24} q="{row["tool_query"][:40]}" items={row["n_items"]} hits={row["hits_curated_record"]} '
              f'urls={row["answer_urls"]} err={bool(row["tool_error"])} {row["seconds"]}s', flush=True)

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT_JSON)
    write_csv(results)


OUT_JSON = ROOT / "data/census/baseline_text_results.json"
OUT_CSV = ROOT / "data/census/baseline_text_results.csv"


def write_csv(results: list):
    """One row per question: object, question, what the tool found, final answer (readable in a spreadsheet)."""
    names = {r["object_id"]: r["name"] for r in csv.DictReader(open(ROOT / "data/census/curated_group.csv"))}
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["opera", "object_id", "domanda", "query_al_tool", "record_trovati", "record_pertinenti",
                    "errore_tool", "risposta"])
        for r in results:
            m = re.search(r"<<<RISPOSTA>>>(.*?)(?:<<<FINE>>>|$)", r["answer"], re.DOTALL)
            w.writerow([names.get(r["object_id"], ""), r["object_id"], r["question"], r["tool_query"],
                        " ;; ".join(r["items"]), r["hits_curated_record"], r["tool_error"] or "",
                        (m.group(1) if m else r["answer"]).strip()])
    print("wrote", OUT_CSV)


if __name__ == "__main__":
    # --csv-only: rebuild the CSV from the saved JSON without calling the agent again
    if "--csv-only" in sys.argv:
        write_csv(json.loads(OUT_JSON.read_text(encoding="utf-8")))
    else:
        main()
