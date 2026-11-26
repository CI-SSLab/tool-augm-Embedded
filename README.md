# AI Agent for European Cultural Heritage Consultation

This project was presented at the **PRESTIGE Workshop** at ICPR 2026 and aims to build an intelligent conversational assistant dedicated to European cultural heritage.

The application allows users to ask questions in natural language about artists and artworks, leveraging a large language model (LLM) integrated with Europeana, one of Europe's main platforms for accessing digital cultural content.

The system was built using CrewAI, Streamlit and Ollama, combining the natural language understanding capabilities of LLMs with reliable data from external sources.

This repository also contains an **extension** of that agent, presented at the ELIZA Research Forum 2026: questions asked with a **photograph**, a multimodal embedding index over a curated collection, and the **Italian General Catalogue of Cultural Heritage (ICCD)** as a second institutional source for **underwater sites**. All extensions are behind feature flags that are off by default, so the agent of the paper runs unchanged. See [Extension: multimodal and underwater cultural heritage](#extension-multimodal-and-underwater-cultural-heritage).

---

## Table of Contents

- [Main Features](#main-features)
- [System Architecture](#system-architecture)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Execution Flow](#execution-flow)
- [Conversational Memory](#conversational-memory)
- [System Transparency](#system-transparency)
- [Installation](#installation)
  - [Option A — Docker (recommended)](#option-a--docker-recommended)
  - [Option B — Local Installation](#option-b--local-installation-without-docker)
- [Example Questions](#example-questions)
- [Extension: multimodal and underwater cultural heritage](#extension-multimodal-and-underwater-cultural-heritage)
- [Possible Future Developments](#possible-future-developments)
- [Citation](#citation)

---

# Main Features

- ChatGPT-like conversational interface
- Retrieval of artistic information via the Europeana API
- Natural language response generation
- Short-term conversational memory
- Technical execution details panel
- Model behaviour control through dedicated tasks

---

# System Architecture

The application is composed of several components working together:

- **Streamlit** → user interface management
- **CrewAI** → intelligent agent orchestration
- **GPT-OSS via Ollama** → text understanding and generation
- **Europeana Tool** → information retrieval from the cultural database
- **Conversational memory** → multi-turn interaction support

The entire system follows a *tool-augmented* approach, where the language model uses external sources to improve the reliability of generated responses.

---

# Technologies Used

- Python
- Streamlit
- CrewAI
- Ollama
- GPT-OSS
- Europeana API
- Requests
- python-dotenv
- Docker / Docker Compose

---

# Project Structure

```bash
project/
│
├── app.py                      # Streamlit interface
├── ui_text.py                  # interface strings, Italian (default) and English
├── crew/
│   ├── agents/qa_agent.py      # text agent of the paper
│   ├── agents/image_agent.py   # extension: agent for questions with a photo (no tools)
│   ├── tasks/answer_task.py    # task and prompt of the paper
│   ├── tasks/image_task.py     # extension: prompt for answers from the retrieved records
│   ├── tasks/underwater_prompt.py  # extension: ICCD prompt block and no-source guardrail
│   └── tool/europeana_tool.py  # Europeana tool of the paper (3-stage cascade)
├── image_search/               # extension: encoder, vector index, search, image tool, UI panel
├── sources/                    # extension: Europeana read by ID, ICCD/ArCo SPARQL
├── evaluation/                 # evaluation scripts of the paper
├── eval/                       # extension: test sets, image evaluation, calibration, figures
├── data/                       # extension: object groups, vector indexes, query sets, demo list
├── scripts/                    # extension: SLURM helpers, demo photo download
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

# File Descriptions

## `app.py`

Manages the Streamlit interface and the main application flow.

It handles:

- receiving user input
- maintaining conversation history
- building short-term memory
- creating and running the agent
- displaying results and technical details

---

## `qa_agent.py`

Contains the configuration of the intelligent agent.

The agent is defined as an art expert and uses the `gpt-oss` model via Ollama.
It can only use the Europeana tool to retrieve information.

---

## `answer_task.py`

Defines the task assigned to the agent.

Includes operational instructions and rules to follow during response generation, such as:

- controlled use of memory
- a single tool call per turn
- mandatory use of data from Europeana
- response generation in Italian

---

## `europeana_tool.py`

Implements the custom tool for accessing the Europeana API.

Main features include:

- query cleaning
- HTTP request handling
- automatic retries on error
- result normalisation
- extraction of title, author, year and artwork links

---

# Execution Flow

When the user submits a question:

1. the system captures the input
2. builds the conversational context
3. creates a new CrewAI agent
4. executes the associated task
5. queries Europeana via the dedicated tool
6. generates the final response
7. cleans the model output
8. updates the conversational memory

---

# Conversational Memory

To maintain continuity across interactions, the system uses a short-term memory composed of:

- the user's last question
- a summary of the last generated response

Memory is only used when genuinely relevant to the new request.

---

# System Transparency

The application includes an optional technical panel that allows users to view:

- the query sent to Europeana
- the results returned by the API
- the raw output generated by the language model

This was implemented to improve system transparency and to facilitate analysis or debugging activities.

---

# Installation

## Option A — Docker (recommended)

Docker is the fastest way to get the project running. It manages Ollama and the application in separate containers with no manual dependency setup required.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- A valid [Europeana API key](https://apis.europeana.eu/en)

### 1. Clone the repository

```bash
git clone https://github.com/USERNAME/tool-augm-europeana.git
cd tool-augm-europeana
```

### 2. Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
EUROPEANA_API_KEY=your_europeana_api_key

OLLAMA_MODEL=gpt-oss:20b
OLLAMA_API_KEY=your_ollama_api_key

# Optional: change the exposed port (default: 8501)
# APP_PORT=8501
```

### 3. Start the containers

```bash
docker compose up --build
```

This will start two services:

- **`tool-ech-ollama`** — the Ollama server (language model backend)
- **`tool-ech-app`** — the Streamlit web application

### 4. Open the application

Once the containers are running, open your browser at:

```
http://localhost:8501
```

> If you changed `APP_PORT` in `.env`, use that port instead.

### Useful commands

```bash
# Run in background (detached mode)
docker compose up -d --build

# Stop all containers
docker compose down

# View logs
docker compose logs -f

# Run the evaluation scripts (single-turn by default, then multi-turn)
docker compose --profile eval run --rm evaluation
docker compose --profile eval run --rm evaluation python evaluation/evaluate_multiturn.py
```

---

## Option B — Local Installation (without Docker)

### 1. Clone the repository

```bash
git clone https://github.com/USERNAME/tool-augm-europeana.git
cd tool-augm-europeana
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the `.env` file

Create a `.env` file in the project root (use `.env.example` as a template):

```env
EUROPEANA_API_KEY=your_europeana_api_key

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_MODEL=gpt-oss:20b
```

> Write the model name as Ollama knows it (`gpt-oss:20b`): the agent adds the `openai/` prefix itself.

### 5. Start Ollama

Make sure [Ollama](https://ollama.com) is installed and running locally, then pull the required model:

```bash
ollama pull gpt-oss:20b
```

### 6. Run the application

```bash
streamlit run app.py
```

---

# Example Questions

- Who is Caravaggio?
- Tell me about Van Gogh
- Which works by Picasso are available on Europeana?
- Compare Monet and Renoir
- Describe a work by Leonardo da Vinci

With the image search on (`ENABLE_IMAGE_SEARCH=true`), attach a photo and ask, for example:

- What is this?
- When does it date from?
- Where was it found?
- Does it come from Pompeii? (the agent reports the place in the record, it does not confirm the premise)

---

# Extension: multimodal and underwater cultural heritage

The extension keeps the design principle of the paper: every factual statement comes from an institutional source, and none may come from the language model or from visual similarity alone.

## What it adds

- **Questions with a photo.** The user attaches a photo and asks a question. The photo identifies the object, the question says what to look for, the record gives the answer.
- **Deterministic routing.** If a photo is attached, or the question is a follow-up on the current object, code sends the turn to the image tool; otherwise the paper's text path runs unchanged. The language model never sees the photo and never sees similarity scores.
- **Curated vector index.** Catalogue photos of a curated group of objects are embedded with EmbeddingGemma 2 (768-d, budget 280 image tokens) and stored as an L2-normalised matrix, one per group and encoder, built incrementally.
- **Decision in code.** Cosine similarity, maximum over the views of each object, then `match` (score ≥ τ and gap to the second object ≥ δ), `ambiguous` (two candidates presented as alternatives) or `no_match`. τ = 0.875 and δ = 0.04 were tuned on a validation split only and then frozen (`image_search/search.py`).
- **Records read by ID.** After the decision the tool reads the records in one Europeana call (`europeana_id:(...)`) and the linked site from the ICCD knowledge graph ArCo, all within a single tool invocation.
- **No match, no language model.** With `no_match` the answer is a fixed text saying that the object is not in the collection; the language model is not called. The `SOURCES` block of image answers is built in code from the retrieved records.
- **ICCD as stage 4 of the text cascade.** When Europeana returns fewer than two results, the text tool also looks among the ICCD records of underwater sites (`location:UnderwaterContext` in ArCo). If no source returns anything, a guardrail replaces the answer with a fixed no-source text.
- **English interface** with `UI_LANG=en`.

## Feature flags

| Variable | Default | Effect |
|---|---|---|
| `ENABLE_IMAGE_SEARCH` | `false` | photo upload, image tool, top-k panel |
| `ENABLE_ICCD_FALLBACK` | `false` | ICCD stage 4 in the text cascade, ICCD prompt block, no-source guardrail |
| `IMAGE_GROUP` | `curated_group` | object group and index: `curated_group` (underwater group, catalogue photos), `curated_group_uw` (plus underwater reference photos), `famous_group` (famous artworks, generality test) |
| `IMAGE_ENCODER` | `google/embeddinggemma-2` | image encoder |
| `EMBED_DEVICE` | `cuda:0` | `cuda:N` (bf16 on Ampere or newer, fp32 otherwise) or `cpu`; never fp16 |
| `IMAGE_COLOUR` | `none` | colour correction of the query photo: `none`, `grayworld`, `clahe` |
| `UI_LANG` | `it` | interface and answer language: `it` or `en` |
| `ARCO_SPARQL_URL` | `http://dati.beniculturali.it/sparql` | ArCo SPARQL endpoint |

With every flag off, the prompt, the tool and the interface are those of the paper.

## Running it

```bash
# Build (or update) the vector index of a group; only new views are embedded
IMAGE_GROUP=curated_group python -m image_search build
python -m image_search selftest          # every index photo must retrieve its own object

# One photo from the command line: top-k objects, decision and the JSON the language model receives
python -m image_search query photo.jpg --colour none

# The app with the extensions on
ENABLE_IMAGE_SEARCH=true ENABLE_ICCD_FALLBACK=true UI_LANG=en streamlit run app.py
```

The demo photos (Wikimedia Commons, open licences, authors and licences in `data/demo/demo_photos.csv`) are downloaded with `python scripts/demo/fetch_demo_photos.py`. On a SLURM machine, `scripts/slurm/ollama.sbatch` starts Ollama as a job and `scripts/slurm/run.sh <command>` runs GPU work inside it.

## Evaluation

Three groups of tests, all scripts in this repository:

1. **Regression** on the paper's 150 text queries and multi-turn sessions, with the flags off and on: the paper's own scripts in `evaluation/`.
2. **Image-only recognition** of famous artworks of the paper's artists, each in several variants (original, crop, angled photo on a wall, warm light with heavy JPEG), plus works of the same artists that are not indexed: `eval/famous/build_famous_group.py` builds the group and the test set (`data/eval/famous_queries.csv`), `eval/famous/evaluate_images.py` scores it.
3. **Photo + question on underwater heritage**: museum photos of indexed objects (C0), underwater photos (C1) and hard negatives (C2) from Wikimedia Commons, `data/eval/underwater_queries.csv` (built by `eval/underwater/build_query_set.py`; labels marked with their provenance). The same `evaluate_images.py` scores recognition, and with `--llm` saves the full answers for the manual check of unsupported claims and false premises.

```bash
python eval/famous/evaluate_images.py --queries data/eval/underwater_queries.csv --group curated_group --split test [--llm]
python eval/underwater/calibrate.py --results <evaluate_images CSV with all splits>   # tau/delta on the val split only
python eval/underwater/figures.py --results <CSV> --famous <CSV>                     # figures for the presentation
```

This is a pilot study: the curated group is small and the validation split has 22 positives.

## Data and licences

Only URLs, identifiers and licences of photos are stored in the repository. Catalogue photos used for the index are cached locally in `data/index_images/` and are not redistributed (most Europeana previews are In Copyright); the index stores only their embeddings. Query and demo photos come from Wikimedia Commons with the licence recorded for each file.

---

# Possible Future Developments

Among possible future improvements:

- integration of additional cultural sources (e.g. the Greek Archaeological Cadastre, which has no public API yet)
- advanced conversational memory
- intelligent result ranking
- automatic suggestion generation for the user

---

# Citation

If you use this project in your research, please cite:

```bibtex
@inproceedings{placeholder,
  % BibTeX entry will be added once the proceedings are available
}
```
