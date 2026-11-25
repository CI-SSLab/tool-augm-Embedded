"""Prompt block appended to the answer task when ENABLE_ICCD_FALLBACK is on.
It adds to the paper's rules without rewriting them; with the flag off nothing changes."""

UNDERWATER_BLOCK = (
    "\n\nESTENSIONE ICCD (reperti e siti sommersi):\n"
    "- Se la domanda riguarda un reperto, una statua o un sito e non un artista, passa al tool "
    "il nome del reperto o del sito come lo scrive l'utente. Non trasformarlo nel nome di un artista.\n"
    "- I record con \"source\": \"ICCD\" sono schede del Catalogo generale dei beni culturali "
    "(Ministero della Cultura). Usa i loro campi description, location e year e cita il loro url in FONTI.\n"
    "- Se il tool non restituisce record pertinenti all'oggetto o al sito chiesto, scrivi che non è "
    "presente nelle fonti consultate e non indicare luogo, datazione, autore o materiale. "
    "Il testo della domanda non è una fonte: non confermare un luogo o un'epoca solo perché li scrive l'utente."
)
