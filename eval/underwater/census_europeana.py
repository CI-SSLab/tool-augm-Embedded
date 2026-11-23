"""Europeana census for the curated underwater group.

Saves the raw JSON of each query to data/census/ (API key stripped) and prints
totals plus the top PROVIDER / DATA_PROVIDER facets, to estimate coverage.

Usage: python eval/underwater/census_europeana.py
"""
import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

URL = "https://api.europeana.eu/record/v2/search.json"
OUT = Path(__file__).resolve().parents[2] / "data" / "census"

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


def main():
    load_dotenv()
    api_key = os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        raise SystemExit("EUROPEANA_API_KEY missing in .env")
    OUT.mkdir(parents=True, exist_ok=True)

    for name, query, qf in QUERIES:
        data = search(api_key, query, qf)
        # The key is also echoed inside each item's "link" (?wskey=...): redact everywhere
        text = json.dumps(data, ensure_ascii=False, indent=1).replace(api_key, "REDACTED")
        assert api_key not in text, "API key leaked into census output"
        (OUT / f"{name}.json").write_text(text, encoding="utf-8")

        items = data.get("items", [])
        with_preview = sum(1 for it in items if it.get("edmPreview"))
        print(f"\n## {name}  query={query}  qf={qf}")
        print(f"total={data.get('totalResults')}  rows={len(items)}  with_edmPreview={with_preview}")
        print("PROVIDER:", top_facet(data, "PROVIDER"))
        print("DATA_PROVIDER:", top_facet(data, "DATA_PROVIDER"))
        for it in items[:5]:
            title = re.sub(r"\s+", " ", (it.get("title") or [""])[0])[:80]
            print(f"  - {title} | {(it.get('year') or [''])[0]} | {(it.get('rights') or [''])[0]}")


if __name__ == "__main__":
    main()
