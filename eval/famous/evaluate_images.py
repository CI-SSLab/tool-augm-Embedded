#!/usr/bin/env python3
"""evaluate_images.py — Evaluation of the image tool on a photo + question test set.

Runs image_search.tool exactly as the app does, one photo per row, and scores the
decision against the expected object (empty = the object is not in the index):
  positive row:  correct_match | correct_ambiguous (expected among the 2) | wrong_match | false_reject
  negative row:  correct_reject | false_match | false_ambiguous
Scores never reach the LLM; with --llm the full turn (image task + LLM) also runs and
the answer is saved next to the question, for the manual unsupported-claim check.

Augmentations are applied here, deterministically, so the test set stores URLs only.

Usage:
    scripts/slurm/run.sh .venv/bin/python eval/famous/evaluate_images.py
    scripts/slurm/run.sh .venv/bin/python eval/famous/evaluate_images.py --llm --limit 20
    ... --queries data/eval/famous_queries.csv --group famous_group --colour none
"""
import argparse
import csv
import io
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
QUERIES = ROOT / "data" / "eval" / "famous_queries.csv"
OUT = ROOT / "eval" / "famous" / "results"
TAU_SWEEP = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
NEAR_DUPLICATE = 0.95  # query this close to an index view is a republication, reported apart


# ── Augmentations ─────────────────────────────────────────────────────────────

def augment(img: Image.Image, name: str, seed: int) -> Image.Image:
    # Controlled degradations that a visitor's photo has and a catalogue scan does not
    rng = np.random.default_rng(seed)
    w, h = img.size
    if not name:
        return img
    if name == "crop":
        # A detail: 60% of the area, random position
        cw, ch = int(w * 0.77), int(h * 0.77)
        x, y = int(rng.integers(0, w - cw + 1)), int(rng.integers(0, h - ch + 1))
        return img.crop((x, y, x + cw, y + ch))
    if name == "perspective":
        # Photo taken at an angle, on a grey wall with margins
        m = 0.12
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = src + np.float32(rng.uniform(-m, m, (4, 2)) * [w, h])
        dst -= dst.min(0) - [w * 0.15, h * 0.15]
        size = (int(dst[:, 0].max() + w * 0.15), int(dst[:, 1].max() + h * 0.15))
        warped = cv2.warpPerspective(np.asarray(img), cv2.getPerspectiveTransform(src, dst), size,
                                     borderValue=(128, 126, 120))
        return Image.fromarray(warped)
    if name == "colour":
        # Warm gallery light, slight blur, heavy JPEG compression
        a = np.asarray(img, dtype=np.float32) * [1.12, 1.0, 0.82]
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=30)
        return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    raise ValueError(f"unknown augmentation: {name}")


# ── Scoring ───────────────────────────────────────────────────────────────────

def outcome(expected: str, decision: str, ranked: list) -> str:
    top = [r["object_id"] for r in ranked]
    if expected:
        if decision == "no_match":
            return "false_reject"
        if decision == "match":
            return "correct_match" if top[0] == expected else "wrong_match"
        return "correct_ambiguous" if expected in top[:2] else "wrong_match"
    return {"no_match": "correct_reject", "match": "false_match"}.get(decision, "false_ambiguous")


def print_summary(rows: list) -> None:
    sets = sorted({r["set"] for r in rows})
    print("\n" + "=" * 92)
    print(f"{'set':16} {'n':>4} {'top1':>7} {'top5':>7} {'near-dup':>9} {'mean s1':>8}   outcomes")
    for s in sets:
        sub = [r for r in rows if r["set"] == s]
        pos = [r for r in sub if r["expected_object_id"]]
        counts = {}
        for r in sub:
            counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
        top1 = f"{100 * sum(r['top1_ok'] for r in pos) / len(pos):6.1f}%" if pos else "     -"
        top5 = f"{100 * sum(r['top5_ok'] for r in pos) / len(pos):6.1f}%" if pos else "     -"
        dup = sum(r["near_duplicate"] for r in pos)
        print(f"{s:16} {len(sub):>4} {top1:>7} {top5:>7} {dup:>9} {np.mean([r['s1'] for r in sub]):8.3f}   "
              + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    # Risk-coverage: accept when s1 >= tau; risk = wrong top-1 among accepted positives, false accepts on negatives
    pos = [r for r in rows if r["expected_object_id"]]
    neg = [r for r in rows if not r["expected_object_id"]]
    print("\n tau   coverage(pos)  accuracy(accepted pos)  false accept(neg)")
    for tau in TAU_SWEEP:
        acc = [r for r in pos if r["s1"] >= tau]
        fa = sum(r["s1"] >= tau for r in neg)
        print(f" {tau:.2f}  {len(acc):4}/{len(pos):<4}       "
              f"{(100 * sum(r['top1_ok'] for r in acc) / len(acc)) if acc else 0:6.1f}%            "
              f"{fa:4}/{len(neg)}")
    print("=" * 92)


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Evaluate the image tool on a photo + question test set")
    p.add_argument("--queries", default=str(QUERIES))
    p.add_argument("--group", default="famous_group", help="object group of the index (data/census/<group>.csv)")
    p.add_argument("--colour", default="none", choices=["none", "grayworld", "clahe"])
    p.add_argument("--llm", action="store_true", help="also run the LLM answer for each row")
    p.add_argument("--limit", type=int, default=0, help="first N rows only (0 = all)")
    p.add_argument("--split", default="", help="only rows with this split (val / test), if the CSV has one")
    p.add_argument("--out", default=str(OUT))
    return p.parse_args()


def main():
    args = parse_args()
    load_dotenv(ROOT / ".env")
    os.environ["IMAGE_GROUP"] = args.group  # read by the tool on its first call
    from image_search import tool
    from image_search.index import cached_image

    queries = list(csv.DictReader(open(args.queries, encoding="utf-8")))
    # Rows nobody has labelled yet cannot be scored
    queries = [q for q in queries if q.get("label_status") != "to_label"
               and (not args.split or q.get("split") == args.split)]
    if args.limit:
        queries = queries[:args.limit]
    if args.llm:
        from image_search.ui import run_image_turn

    rows = []
    for n, q in enumerate(queries, 1):
        try:
            img = augment(Image.open(cached_image(q["image_url"])).convert("RGB"), q["augment"],
                          seed=int(q["query_id"][1:]))
        except Exception as e:
            log.warning("%s: image not available (%s)", q["query_id"], e)
            continue
        t0 = time.time()
        result = json.loads(tool.image_search(img, colour=args.colour))
        ranked = tool.get_last_image_trace()["ranked"]
        latency = time.time() - t0
        top = [r["object_id"] for r in ranked]
        row = dict(q, decision=result["decision"], top1=top[0], s1=round(ranked[0]["score"], 4),
                   s2=round(ranked[1]["score"], 4) if len(ranked) > 1 else 0.0,
                   top5="; ".join(top), top1_ok=int(top[0] == q["expected_object_id"]),
                   top5_ok=int(q["expected_object_id"] in top), latency_s=round(latency, 3),
                   near_duplicate=int(bool(q["expected_object_id"]) and ranked[0]["score"] >= NEAR_DUPLICATE),
                   outcome=outcome(q["expected_object_id"], result["decision"], ranked))
        if args.llm:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=92)
            raw, _ = run_image_turn(q["question"], buf.getvalue(), SimpleNamespace(current_object=None))
            row["answer"] = raw
        rows.append(row)
        log.info("[%d/%d] %-14s %-16s %-17s s1=%.3f", n, len(queries), q["set"], row["outcome"],
                 row["top1"][:17], row["s1"])

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"results_images_{args.group}_{args.colour}_{run_id}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %s", path)
    print_summary(rows)


if __name__ == "__main__":
    main()
