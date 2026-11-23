#!/usr/bin/env python3
"""evaluation/evaluate_multiturn.py run unchanged on the underwater curated group.

Seeds and scenario templates change; agent, memory, CRR/SIR/TDR/SAR scoring, CSV and
summary are the paper's own code. Same A/B/C structure, underwater questions:

  A  co-reference chain   T1 "Tell me about {X}."  T2 "When does it date from?"  T3 "Where was it found?"
     (CRR: X still in the tool query on T2/T3)
  B  object switch        T1 "Tell me about {X1}."  T2 "Tell me about {X2}."
     (SIR: X2 in the query, X1 not; neighbours in the seed list are similar objects)
  C  object -> site       T1 "Where was {X} found?"  T2 "What else is known about that site?"
     (the follow-up depends on the site named in T1: the object-to-site link)
T1 always starts with "Tell me about" or names X directly, because update_current_artist()
only recognises a new entity after the intro prefixes in evaluate_multiturn._ARTIST_INTROS.

Usage:
    scripts/slurm/run.sh .venv/bin/python eval/underwater/evaluate_multiturn_underwater.py [--dry-run]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT / "eval" / "underwater"))

import evaluate_multiturn as base  # noqa: E402
from evaluate_underwater import OUT, UNDERWATER_SEEDS  # noqa: E402

if __name__ == "__main__":
    base.MT_ARTIST_SEEDS = UNDERWATER_SEEDS
    base.SCENARIO_A_TURNS = ["Tell me about {artist}.", "When does it date from?", "Where was it found?"]
    base.SCENARIO_B_TURNS = ["Tell me about {artist_1}.", "Tell me about {artist_2}."]
    base.SCENARIO_C_TURNS = ["Where was {artist} found?", "What else is known about that site?"]
    base.MIN_RECORDS = 0  # same reason as evaluate_underwater.py
    if "--out" not in sys.argv:
        sys.argv += ["--out", OUT]
    base.main()
