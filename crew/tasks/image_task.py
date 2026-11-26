from crewai import Task

from ui_text import ENGLISH_ANSWER_BLOCK, lang

# Fixed answer for no_match: the LLM never sees the photo, so it has nothing to describe.
# Decided in code, the LLM is not called at all.
NO_MATCH_ANSWER = (
    "Non ho riconosciuto l'oggetto della foto fra i reperti e i siti che posso consultare, "
    "quindi non ho una scheda di Europeana o del Catalogo generale dei beni culturali (ICCD) "
    "da cui ricavare luogo, datazione o provenienza.\n\n"
    "FONTI: nessuna fonte disponibile"
)
NO_MATCH_ANSWER_EN = (
    "I did not recognise the object in the photo among the artefacts and sites I can consult, "
    "so I have no record from Europeana or the ICCD General Catalogue of Cultural Heritage "
    "to give its place, date or provenance.\n\n"
    "SOURCES: no source available"
)


def build_image_task(agent) -> Task:
    #CrewAI replaces {question} and {tool_result} with the values
    #passed to crew.kickoff(inputs={...})
    return Task(
        description=(
            "Domanda dell'utente: {question}\n\n"
            "Schede trovate dal sistema di ricerca per immagini (JSON):\n{tool_result}\n\n"

            "Regole:\n"
            "1) Non vedi la foto. Rispondi alla domanda in italiano, in 3-6 frasi, usando solo i campi "
            "dei candidati: title, creator, year, description, place_in_record_findspot_or_museum_unspecified, address, current_location e site. "
            "Se i testi della scheda sono in un'altra lingua, traducili.\n"
            "2) Se 'decision' è 'ambiguous', presenta i due candidati come alternative possibili "
            "e non sceglierne uno.\n"
            "3) Il campo 'place_in_record_findspot_or_museum_unspecified' è il luogo registrato dalla fonte: la scheda non dice se è il luogo "
            "del ritrovamento o quello dove l'oggetto è conservato, quindi riportalo come "
            "'luogo indicato nella scheda'.\n"
            "4) Se il dato chiesto non è nella scheda, scrivi che la scheda non lo riporta. "
            "Puoi aggiungere al massimo una frase di contesto generale, segnalandola come "
            "conoscenza generale, ma mai luoghi, date, autori o materiali che non siano nella scheda. "
            "Non dire che l'oggetto è una copia se la scheda non lo dice.\n"
            "5) Il testo della domanda non è una fonte: se l'utente indica un luogo o un'epoca diversi "
            "da quelli della scheda, riporta quelli della scheda e non confermare la premessa.\n\n"

            "Formato dell'output (obbligatorio):\n"
            "Racchiudi la risposta finale tra i marcatori <<<RISPOSTA>>> e <<<FINE>>>. "
            "Termina con una sezione 'FONTI:' con gli url dei candidati e dei siti, uno per riga."
        ) + (ENGLISH_ANSWER_BLOCK if lang() == "en" else ""),
        expected_output=(
            "Testo italiano racchiuso tra <<<RISPOSTA>>> e <<<FINE>>> "
            "con sezione FONTI conclusiva."
        ),
        agent=agent,
        async_execution=False,
    )
