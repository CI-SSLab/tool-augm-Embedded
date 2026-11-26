"""Interface strings in Italian (the paper's app, default) and English (UI_LANG=en).

With UI_LANG unset every string is the original Italian one, so the app is unchanged."""
import os

TEXT = {
    "it": {
        "page_title": "Esperto d'arte",
        "invalid_retry": "Il modello ha prodotto una risposta non valida dopo più tentativi. "
                         "Prova a riformulare la domanda o a pulire la chat.",
        "details": "🔎 Dettagli esecuzione",
        "details_caption": "Traccia tecnica della risposta generata",
        "tab_input": "Input", "tab_api": "API Europeana", "tab_llm": "LLM / CrewAI", "tab_image": "Ricerca immagine",
        "user_question": "**Domanda dell'utente**",
        "tool_query": "**Query inviata al tool**",
        "thread_artist": "**Artista corrente del thread**",
        "none": "(nessuno)",
        "api_output": "**Output restituito da Europeana**",
        "llm_output": "**Output grezzo di CrewAI**",
        "sidebar_header": "ℹ️ Informazioni",
        "model": "**Modello AI:**",
        "current_artist": "**Artista corrente:**",
        "examples": "### Esempi di domande",
        "example_questions": ("Chi è Caravaggio?", "Chi è Picasso?", "Chi è Van Gogh?"),
        "title": "🎨 Esperto d'arte",
        "caption": "Assistente AI che risponde a domande su artisti utilizzando Europeana.",
        "empty_hint": "Prova a chiedere qualcosa su un artista europeo.",
        "clear": "Pulisci chat",
        "input_photo": "Scrivi la tua domanda e allega una foto, se vuoi",
        "ask_photo": "Cosa vuoi sapere dell'oggetto nella foto?",
        "input": "Scrivi la tua domanda, ad esempio: Chi è Caravaggio?",
        "spinner": "Sto cercando la risposta...",
        "no_valid": "Non sono riuscito a generare una risposta valida. Prova a riformulare la domanda.",
        "error": "Errore",
        "error_details": "Dettagli errore",
        "user_photo": "**Foto dell'utente**",
        "decision": "**Decisione:**",
        "photo_query": "(foto caricata)",
        "object_query": "(oggetto corrente del thread)",
    },
    "en": {
        "page_title": "Art expert",
        "invalid_retry": "The model produced an invalid answer after several attempts. "
                         "Try rephrasing the question or clearing the chat.",
        "details": "🔎 Execution details",
        "details_caption": "Technical trace of the generated answer",
        "tab_input": "Input", "tab_api": "Europeana API", "tab_llm": "LLM / CrewAI", "tab_image": "Image search",
        "user_question": "**User question**",
        "tool_query": "**Query sent to the tool**",
        "thread_artist": "**Current artist in thread**",
        "none": "(none)",
        "api_output": "**Output returned by the tool**",
        "llm_output": "**Raw CrewAI output**",
        "sidebar_header": "ℹ️ Information",
        "model": "**AI model:**",
        "current_artist": "**Current artist:**",
        "examples": "### Example questions",
        "example_questions": ("Who is Caravaggio?", "Who is Picasso?", "Who is Van Gogh?"),
        "title": "🎨 Art expert",
        "caption": "AI assistant that answers questions on cultural heritage using Europeana and the ICCD catalogue.",
        "empty_hint": "Ask about a European artist, or attach a photo of an artwork with your question.",
        "clear": "Clear chat",
        "input_photo": "Write your question and attach a photo, if you like",
        "ask_photo": "What would you like to know about the object in the photo?",
        "input": "Write your question, for example: Who is Caravaggio?",
        "spinner": "Looking for the answer...",
        "no_valid": "I could not generate a valid answer. Try rephrasing the question.",
        "error": "Error",
        "error_details": "Error details",
        "user_photo": "**User photo**",
        "decision": "**Decision:**",
        "photo_query": "(uploaded photo)",
        "object_query": "(current object in thread)",
    },
}


# Appended to the answer prompts when UI_LANG=en; the internal markers stay the same
ENGLISH_ANSWER_BLOCK = (
    "\n\nLANGUAGE: write the final answer in English, still between <<<RISPOSTA>>> and <<<FINE>>>. "
    "Use 'SOURCES:' instead of 'FONTI:'. If you have no url, write 'SOURCES: no source available'. "
    "Translate the record fields into English, but keep titles as they appear in the record."
)


def lang() -> str:
    return "en" if os.getenv("UI_LANG", "").strip().lower() == "en" else "it"


def t(key: str):
    return TEXT[lang()][key]


if __name__ == "__main__":  # both languages must define the same keys
    assert TEXT["it"].keys() == TEXT["en"].keys(), set(TEXT["it"]) ^ set(TEXT["en"])
    print("ui_text.py self-check ok")
