#!/usr/bin/env python3
"""calibrate.py — Tune tau and delta on the validation split, then score the test split once.

Works on the scores already saved by eval/famous/evaluate_images.py (s1, s2, top-5 order),
so no GPU is needed. The decision rule is the tool's own (image_search.search.decide):
  match      s1 >= tau and s1 - s2 >= delta
  ambiguous  s1 >= tau and s1 - s2 <  delta
  no_match   s1 <  tau
A decision is correct when a positive gets its object (match on top-1, or ambiguous with
the object among the first two) and when a negative gets no_match.

Objective on val: balanced accuracy = (credit on positives / positives + correct negatives /
negatives) / 2. A correct ambiguous answer earns half credit: the user gets two records
instead of one, and with full credit a large delta turns every answer into "ambiguous".
Ties go to the higher tau, then the higher delta: fewer wrong records.

Usage:
    python eval/underwater/calibrate.py --results eval/underwater/results/images/results_images_curated_group_none_<id>.csv
"""
import argparse
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "data" / "eval" / "underwater_queries.csv"

# ── Constants ─────────────────────────────────────────────────────────────────
AMBIGUOUS_CREDIT = 0.5
TAUS = np.round(np.arange(0.70, 0.985, 0.005), 3)
DELTAS = np.round(np.arange(0.0, 0.105, 0.005), 3)


def decide(s1: float, s2: float, tau: float, delta: float) -> str:
    if s1 < tau:
        return "no_match"
    return "match" if s1 - s2 >= delta else "ambiguous"


def correct(r: dict, decision: str) -> bool:
    exp, top = r["expected_object_id"], r["top5"].split("; ")
    if not exp:
        return decision == "no_match"
    if decision == "match":
        return top[0] == exp
    return decision == "ambiguous" and exp in top[:2]


def score(rows: list, tau: float, delta: float) -> dict:
    pos = [r for r in rows if r["expected_object_id"]]
    neg = [r for r in rows if not r["expected_object_id"]]
    def credit(r):
        d = decide(float(r["s1"]), float(r["s2"]), tau, delta)
        return (AMBIGUOUS_CREDIT if d == "ambiguous" else 1.0) if correct(r, d) else 0.0
    acc_pos = np.mean([credit(r) for r in pos]) if pos else 0.0
    acc_neg = np.mean([credit(r) for r in neg]) if neg else 0.0
    return {"balanced": (acc_pos + acc_neg) / 2, "pos": acc_pos, "neg": acc_neg, "n_pos": len(pos), "n_neg": len(neg)}


def report(rows: list, tau: float, delta: float, title: str):
    print(f"\n{title}  (tau={tau:.3f}, delta={delta:.3f})")
    print(f"{'set':5} {'n':>4}  {'match ok':>9} {'ambig ok':>9} {'wrong':>6} {'no_match':>9}   correct")
    for s in ("C0", "C1", "C2"):
        sub = [r for r in rows if r["set"] == s]
        if not sub:
            continue
        dec = [(r, decide(float(r["s1"]), float(r["s2"]), tau, delta)) for r in sub]
        m_ok = sum(d == "match" and correct(r, d) for r, d in dec)
        a_ok = sum(d == "ambiguous" and correct(r, d) for r, d in dec)
        nm = sum(d == "no_match" for _, d in dec)
        wrong = sum(d != "no_match" and not correct(r, d) for r, d in dec)
        ok = sum(correct(r, d) for r, d in dec)
        print(f"{s:5} {len(sub):>4}  {m_ok:>9} {a_ok:>9} {wrong:>6} {nm:>9}   {100 * ok / len(sub):5.1f}%")


def main():
    p = argparse.ArgumentParser(description="Tune tau/delta on val, score test once")
    p.add_argument("--results", required=True, help="evaluate_images.py CSV with all splits")
    p.add_argument("--queries", default=str(QUERIES), help="query CSV holding the current split column")
    args = p.parse_args()

    split = {q["query_id"]: q["split"] for q in csv.DictReader(open(args.queries, encoding="utf-8"))}
    rows = [dict(r, split=split.get(r["query_id"], r.get("split", ""))) for r in
            csv.DictReader(open(args.results, encoding="utf-8"))]
    val = [r for r in rows if r["split"] == "val"]
    test = [r for r in rows if r["split"] == "test"]

    grid = [(score(val, t, d), t, d) for t in TAUS for d in DELTAS]
    best, tau, delta = max(grid, key=lambda g: (round(g[0]["balanced"], 6), g[1], g[2]))
    print(f"val: {best['n_pos']} positives, {best['n_neg']} negatives")
    print(f"best balanced accuracy {100 * best['balanced']:.1f}% "
          f"(positives {100 * best['pos']:.1f}%, negatives {100 * best['neg']:.1f}%)")
    print("\n tau    delta  balanced  positives  negatives   (best delta per tau, val)")
    for t in TAUS[::4]:
        s, _, d = max(((score(val, t, d), t, d) for d in DELTAS), key=lambda g: (round(g[0]["balanced"], 6), g[2]))
        print(f" {t:.3f}  {d:.3f}   {100 * s['balanced']:5.1f}%    {100 * s['pos']:5.1f}%     {100 * s['neg']:5.1f}%")

    report(val, tau, delta, "VAL with the chosen values")
    report(test, 0.80, 0.03, "TEST with the provisional values")
    report(test, tau, delta, "TEST with the frozen values")


if __name__ == "__main__":
    main()
