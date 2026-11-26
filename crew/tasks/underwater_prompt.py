"""Additions to the answer task when ENABLE_ICCD_FALLBACK is on: a prompt block appended
to the paper's rules, and a guardrail that enforces graceful degradation in code.
With the flag off nothing changes."""
import json

from crew.tool.europeana_tool import get_last_tool_trace
from ui_text import lang

UNDERWATER_BLOCK = (
    "\n\nESTENSIONE ICCD (reperti e siti sommersi):\n"
    "- Se la domanda riguarda un reperto, una statua o un sito e non un artista, passa al tool "
    "il nome del reperto o del sito come lo scrive l'utente. Non trasformarlo nel nome di un artista.\n"
    "- I record con \"source\": \"ICCD\" sono schede del Catalogo generale dei beni culturali "
    "(Ministero della Cultura). Usa i loro campi description, location, address e year e cita il loro url in FONTI.\n"
    "- Se il tool non restituisce record pertinenti all'oggetto o al sito chiesto, scrivi che non è "
    "presente nelle fonti consultate e non indicare luogo, datazione, autore o materiale. "
    "Il testo della domanda non è una fonte: non confermare un luogo o un'epoca solo perché li scrive l'utente."
)

NO_SOURCE_ANSWER = (
    "<<<RISPOSTA>>>\n"
    "{name}: non ho trovato schede nelle fonti consultate (Europeana e Catalogo generale dei beni "
    "culturali ICCD). Senza una scheda non posso indicarne luogo, datazione, autore o materiale.\n\n"
    "FONTI: nessuna fonte disponibile\n"
    "<<<FINE>>>"
)
NO_SOURCE_ANSWER_EN = (
    "<<<RISPOSTA>>>\n"
    "{name}: I found no record in the sources I can query (Europeana and the ICCD General Catalogue "
    "of Cultural Heritage). Without a record I cannot give its place, date, author or material.\n\n"
    "SOURCES: no source available\n"
    "<<<FINE>>>"
)


def no_source_guardrail(output):
    """CrewAI task guardrail: if the tool returned no record, replace the LLM answer with a fixed
    text, because the prompt rule alone is not followed by gpt-oss-20b (journey.md, 25 Nov).
    shortcut: reads the tool module's last trace, so a turn where the LLM skips the tool sees the
    previous turn's trace; fine while tool discipline is ~100%, revisit if it drops."""
    try:
        result = json.loads(get_last_tool_trace().get("result") or "")
    except ValueError:
        return True, output.raw  # tool not called or not JSON: keep the answer
    if result.get("items"):
        return True, output.raw
    text = NO_SOURCE_ANSWER_EN if lang() == "en" else NO_SOURCE_ANSWER
    return True, text.format(name=result.get("query") or ("The requested object" if lang() == "en" else "L'oggetto richiesto"))


if __name__ == "__main__":  # self-check with fake traces
    from types import SimpleNamespace

    import crew.tool.europeana_tool as tool

    out = SimpleNamespace(raw="<<<RISPOSTA>>>inventato<<<FINE>>>")
    tool._LAST_TRACE.update(result=json.dumps({"query": "Antikythera Youth", "items": [], "error": "x"}))
    ok, text = no_source_guardrail(out)
    assert ok and "Antikythera Youth: non ho trovato" in text and "<<<FINE>>>" in text
    tool._LAST_TRACE.update(result=json.dumps({"query": "Punta Epitaffio", "items": [{"title": "t"}]}))
    assert no_source_guardrail(out) == (True, out.raw)
    tool._LAST_TRACE.update(result="")
    assert no_source_guardrail(out) == (True, out.raw)
    print("underwater_prompt.py self-check ok")
