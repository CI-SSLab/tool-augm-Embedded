#!/usr/bin/env python3
"""evaluation/evaluate.py run unchanged on the underwater curated group.

Seeds, question templates and output folder change; sampling, agent,
baseline, scoring, CSV and summary are the paper's own code.

Usage:
    scripts/slurm/run.sh .venv/bin/python eval/underwater/evaluate_underwater.py [evaluate.py options]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))

import evaluate as base  # noqa: E402

# Curated group (data/census/curated_group.csv), named as a user would type them
UNDERWATER_SEEDS = [
    "Ulysses of Punta Epitaffio", "Antonia Augusta", "Dionysus with ivy wreath",
    "Artemision Bronze", "Jockey of Artemision", "Antikythera Youth", "Antikythera Philosopher",
    "Punta Epitaffio nymphaeum", "Baia underwater park", "Portus Julius", "Miseno harbour",
]
OUT = str(ROOT / "eval" / "underwater" / "results")

if __name__ == "__main__":
    base.ARTIST_SEEDS = UNDERWATER_SEEDS
    # Same three question types as the paper, worded for objects and sites
    base.QUESTION_TEMPLATES = ["Tell me about {artist}.", "Where was {artist} found?", "When does {artist} date from?"]
    base.Q_LABELS = ["identification", "provenance", "temporal"]
    # Paper filter keeps seeds with >= 2 tool records: only "Antonia Augusta" passes (as coins). 0 = keep all.
    base.MIN_RECORDS = 0
    if "--out" not in sys.argv:
        sys.argv += ["--out", OUT]
    base.main()
