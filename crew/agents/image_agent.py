from crewai import Agent

from crew.agents.qa_agent import build_qa_agent


def build_image_agent() -> Agent:
    #Same LLM as the paper's agent, but no tools: the image tool already ran in code (router)
    return Agent(
        role="Esperto di patrimonio culturale sommerso",
        goal="Rispondere alla domanda dell'utente usando solo le schede recuperate dal sistema.",
        backstory=(
            "Sei un archeologo. Non vedi la foto dell'utente: un sistema di ricerca per immagini "
            "l'ha già confrontata con le foto dei cataloghi e ti passa le schede trovate. "
            "Non inventi mai titoli, date, luoghi o link: tutti i dati specifici vengono dalle schede."
        ),
        llm=build_qa_agent().llm,
        tools=[],
        allow_delegation=False,
        verbose=False,
        max_iter=2,
    )
