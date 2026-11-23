"""Europeana census for the curated underwater group.

Same layout as evaluation/evaluate.py: query list as a module constant, main()
with --out / --dry-run, CSV summary. Saves the raw JSON of each query (API key
redacted) and census_summary.csv with totals and the top PROVIDER / DATA_PROVIDER facets.

Usage:
    python eval/underwater/census_europeana.py [--out data/census] [--dry-run]
"""
import argparse
import csv
import json
import logging
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
URL = "https://api.europeana.eu/record/v2/search.json"
OUT = ROOT / "data" / "census"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

UNDERWATER = '"underwater archaeology" OR "archeologia subacquea" OR "υποβρύχια αρχαιολογία"'

# (file name, query, extra qf filters)
QUERIES = [
    ("riace", "Riace", ["TYPE:IMAGE"]),
    ("satiro_danzante", '"Satiro danzante"', ["TYPE:IMAGE"]),
    ("artemision", "Artemision", ["TYPE:IMAGE"]),
    ("antikythera", "Antikythera", ["TYPE:IMAGE"]),
    ("pavlopetri", "Pavlopetri", ["TYPE:IMAGE"]),
    ("baia", "Baia", ["TYPE:IMAGE"]),
    ("punta_epitaffio", '"Punta Epitaffio"', ["TYPE:IMAGE"]),
    # Refined after round 1: "Baia" hits bays, "Artemision" hits the Ephesus temple
    ("baiae", 'Baiae OR "Campi Flegrei" OR "Phlegraean" OR "Castello di Baia"', ["TYPE:IMAGE"]),
    ("ninfeo_claudio", '"Ninfeo di Claudio" OR "ninfeo" AND Baia', ["TYPE:IMAGE"]),
    ("portus_julius", '"Portus Julius" OR "Portus Iulius"', ["TYPE:IMAGE"]),
    ("bronzi_riace", '"Bronzi di Riace" OR "Riace Bronze" OR "Riace-Krieger" OR "Krieger von Riace"', ["TYPE:IMAGE"]),
    ("artemision_bronze", '"Capo Artemisio" OR "Kap Artemision" OR "Cape Artemision" OR "Zeus von Artemision" OR "Poseidon von Artemision" OR "jockey of Artemision"', ["TYPE:IMAGE"]),
    ("antikythera_ephebe", '"Ephebe of Antikythera" OR "Jüngling von Antikythera" OR "Efebo di Anticitera" OR "Έφηβος των Αντικυθήρων"', ["TYPE:IMAGE"]),
    ("mazara", '"Mazara del Vallo" AND (satiro OR satyr OR Satyr)', ["TYPE:IMAGE"]),
    ("underwater_italy", UNDERWATER, ["COUNTRY:italy"]),
    ("underwater_greece", UNDERWATER, ["COUNTRY:greece"]),
]


def search(api_key: str, query: str, qf: list) -> dict:
    params = {
        "wskey": api_key, "query": query, "qf": qf, "rows": 100,
        "profile": "rich facets", "facet": "PROVIDER,DATA_PROVIDER",
    }
    r = requests.get(URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def top_facet(data: dict, name: str, n: int = 5) -> list:
    for f in data.get("facets", []):
        if f.get("name") == name:
            return [(v["label"], v["count"]) for v in f.get("fields", [])[:n]]
    return []


CSV_FIELDS = ["name", "query", "qf", "total", "rows", "with_edmPreview", "top_provider", "top_data_provider"]


def parse_args():
    p = argparse.ArgumentParser(description="Europeana census for the underwater curated group")
    p.add_argument("--out", type=str, default=str(OUT))
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    if args.dry_run:
        for name, query, qf in QUERIES:
            print(f"  {name:20} query={query}  qf={qf}")
        return

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        raise SystemExit("EUROPEANA_API_KEY missing in .env")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    summary = []
    for name, query, qf in QUERIES:
        data = search(api_key, query, qf)
        # The key is also echoed inside each item's "link" (?wskey=...): redact everywhere
        text = json.dumps(data, ensure_ascii=False, indent=1).replace(api_key, "REDACTED")
        assert api_key not in text, "API key leaked into census output"
        (out / f"{name}.json").write_text(text, encoding="utf-8")

        items = data.get("items", [])
        row = {
            "name": name, "query": query, "qf": ";".join(qf), "total": data.get("totalResults"),
            "rows": len(items), "with_edmPreview": sum(1 for it in items if it.get("edmPreview")),
            "top_provider": "; ".join(f"{l} ({c})" for l, c in top_facet(data, "PROVIDER")),
            "top_data_provider": "; ".join(f"{l} ({c})" for l, c in top_facet(data, "DATA_PROVIDER")),
        }
        summary.append(row)
        log.info("%-20s total=%-6s rows=%-3s preview=%s", name, row["total"], row["rows"], row["with_edmPreview"])
        for it in items[:5]:
            title = re.sub(r"\s+", " ", (it.get("title") or [""])[0])[:80]
            log.info("    - %s | %s | %s", title, (it.get("year") or [""])[0], (it.get("rights") or [""])[0])

    with open(out / "census_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(summary)
    log.info("CSV saved -> %s  (%d queries)", out / "census_summary.csv", len(summary))


if __name__ == "__main__":
    main()
