"""CLI.

  python -m image_search build              build or update the index from curated_group.csv
  python -m image_search query PHOTO [-k 5]  top-k objects and decision for one photo
  python -m image_search selftest           every cached index photo must retrieve its own object first
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(prog="image_search")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    q = sub.add_parser("query")
    q.add_argument("photo")
    q.add_argument("-k", type=int, default=5)
    sub.add_parser("selftest")
    for s in sub.choices.values():
        s.add_argument("--budget", type=int, default=280)
    args = p.parse_args()

    from image_search import index, search
    from image_search.encoder import Encoder, load_image

    enc = Encoder(budget=args.budget)
    if args.cmd == "build":
        index.build(enc)
        return

    emb, rows = index.load_index(index.index_dir(enc.slug))
    if args.cmd == "query":
        ranked = search.rank_objects(enc.embed([load_image(args.photo)])[0], emb, rows)
        decision, ids = search.decide(ranked)
        for oid, s, i in ranked[:args.k]:
            print(f"{s:.3f}  {oid:26} {rows[i]['source']:9} {rows[i]['view_id']}")
        print(f"decision: {decision} {ids}")
    else:
        images = [load_image(index.cached_image(r["image_url"])) for r in rows]
        fresh = enc.embed(images)
        wrong = [(r["object_id"], search.rank_objects(v, emb, rows)[0][0]) for r, v in zip(rows, fresh)
                 if search.rank_objects(v, emb, rows)[0][0] != r["object_id"]]
        drift = float(abs((fresh * emb).sum(1) - 1).max())
        print(f"selftest: {len(rows) - len(wrong)}/{len(rows)} views retrieve their own object; "
              f"max |1 - cos(fresh, stored)| = {drift:.4f}")
        for own, got in wrong:
            print(f"  {own} -> {got}")
        assert not wrong and drift < 0.02


if __name__ == "__main__":
    main()
