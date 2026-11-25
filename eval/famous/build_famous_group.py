"""Build the famous-artworks group (index) and its image test set.

Generality test of the image tool outside the underwater domain. For each of the
paper's ARTIST_SEEDS, Wikidata gives the most famous works (by sitelinks) with their
Commons image and owning collection. A work enters the index only if Europeana has a
record of it from that same collection (title phrase + creator + data provider), so the
ground truth needs no visual check and does not depend on the encoder under test.

Outputs:
  data/census/famous_group.csv     index group, same columns used by image_search.index
  data/eval/famous_queries.csv     test set: one photo + one question per row (URLs only)
    F0       Commons image of an indexed work (different source from the index photo)
    F0_<aug> the same photo with a controlled degradation (crop, perspective, colour cast)
    F2       Commons image of a famous work of the same artist that is NOT indexed (must be no_match)

Usage:
    python eval/famous/build_famous_group.py [--per-artist 2] [--dry-run]
"""
import argparse
import csv
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation"))

from crew.tool.europeana_tool import _creator_matches  # noqa: E402
from sources.europeana import SEARCH_URL, item_url  # noqa: E402

GROUP_OUT = ROOT / "data" / "census" / "famous_group.csv"
QUERIES_OUT = ROOT / "data" / "eval" / "famous_queries.csv"
WIKIDATA = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "heritage-image-eval/0.1 (research prototype)"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
WORKS_PER_ARTIST = 5     # famous works looked up on Wikidata per artist
MAX_VIEWS = 3            # Europeana records kept per work
LANGS = ("en", "it", "nl", "de", "fr", "es")
AUGMENTS = ["crop", "perspective", "colour"]

# Question templates, one per query photo in rotation; the last one carries a false premise
QUESTION_TEMPLATES = [
    "Cos'è quest'opera?",
    "Chi l'ha realizzata?",
    "A che anno risale?",
    "È un'opera di {wrong_artist}?",
]
Q_LABELS = ["identification", "creator", "temporal", "false_premise"]

# Record types that are copies of the work, not the work (prints, drawings, photos after the painting)
_COPY_TYPES = ("print", "drawing", "photograph", "prent", "tekening", "foto", "druck", "zeichnung", "stampa",
               "disegno", "gravure", "engraving", "estampe", "dessin")

# Words too common in museum names to say that two names are the same collection
_GENERIC = {"museum", "museo", "musée", "musee", "national", "nationale", "nazionale", "gallery", "galerie",
            "galleria", "collection", "collezione", "state", "staatliche", "kunst", "royal", "royaux", "beaux",
            "fine", "arts", "art", "des", "the", "and", "von", "voor", "museums", "foundation"}

GROUP_FIELDS = ["object_id", "name", "typology", "status", "object_source", "europeana_ids", "object_title",
                "object_url", "n_views", "rights", "data_providers", "arco_site_id", "artist", "collection",
                "wikidata", "note"]
QUERY_FIELDS = ["query_id", "set", "expected_object_id", "artist", "work", "wikidata", "image_url", "augment",
                "q_label", "question", "premise", "premise_false"]


def _words(text: str) -> set:
    return {w for w in re.findall(r"[^\W\d_]{5,}", text.lower()) if w not in _GENERIC}


def _wikidata(query: str) -> list:
    # Retry with backoff on 5xx, like the paper's tool does with Europeana
    for attempt in range(3):
        r = requests.get(WIKIDATA, params={"query": query, "format": "json"}, headers=HEADERS, timeout=120)
        if r.status_code < 500:
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def wikidata_works(artist: str) -> list:
    # Wikidata's own entity search ranks the famous one first ("Vermeer" -> Johannes, not Jan van Haarlem)
    r = requests.get("https://www.wikidata.org/w/api.php", headers=HEADERS, timeout=60, params={
        "action": "wbsearchentities", "search": artist, "language": "en", "type": "item", "limit": 10, "format": "json"})
    r.raise_for_status()
    hits = [h for h in r.json().get("search", [])
            if re.search(r"painter|sculptor|artist|polymath", h.get("description", ""), re.IGNORECASE)]
    if not hits:
        return []
    qid = hits[0]["id"]
    # Most famous paintings and sculptures of the artist, with Commons image, titles and collections
    query = f"""
    SELECT ?w (SAMPLE(?en) AS ?name) (SAMPLE(?img) AS ?image) (MAX(?sl) AS ?links)
           (GROUP_CONCAT(DISTINCT ?t; separator="|") AS ?titles)
           (GROUP_CONCAT(DISTINCT ?cl; separator="|") AS ?colls) WHERE {{
      BIND(wd:{qid} AS ?a)
      VALUES ?type {{ wd:Q3305213 wd:Q860861 }}
      ?w wdt:P170 ?a ; wdt:P31 ?type ; wdt:P18 ?img ; wikibase:sitelinks ?sl ; rdfs:label ?t .
      FILTER(LANG(?t) IN ({", ".join(f'"{lang}"' for lang in LANGS)}))
      OPTIONAL {{ ?w rdfs:label ?en . FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?w wdt:P195 ?c . ?c rdfs:label ?cl . FILTER(LANG(?cl) IN ({", ".join(f'"{lang}"' for lang in LANGS)})) }}
    }} GROUP BY ?w ORDER BY DESC(?links) LIMIT {WORKS_PER_ARTIST}"""
    return [{"wikidata": b["w"]["value"].rsplit("/", 1)[-1], "name": b.get("name", {}).get("value", ""),
             "image": b["image"]["value"], "titles": [t for t in b["titles"]["value"].split("|") if t],
             "collections": [c for c in b.get("colls", {}).get("value", "").split("|") if c]}
            for b in _wikidata(query)]


def europeana_views(work: dict, artist: str, api_key: str) -> list:
    # Records of the work held by its own collection: title phrase, creator and data provider must agree
    coll_words = set().union(*(_words(c) for c in work["collections"])) if work["collections"] else set()
    if not coll_words:
        return []
    found = {}
    for title in dict.fromkeys(work["titles"]):
        r = requests.get(SEARCH_URL, params={"wskey": api_key, "query": f'title:"{title}" AND who:"{artist.split()[-1]}"', "qf": "TYPE:IMAGE",
                                             "rows": 20, "profile": "rich"}, timeout=30)
        if r.status_code != 200:
            continue
        for it in r.json().get("items", []):
            provider = " ".join(it.get("dataProvider", []))
            # Providers fill different creator fields (Rijksmuseum leaves dcCreator empty)
            creator = " ".join(str(it.get(f, "")) for f in ("dcCreator", "dcCreatorLangAware", "edmAgentLabel"))
            kind = str(it.get("dcTypeLangAware", "")).lower()
            if (it.get("edmPreview") and _creator_matches(creator, artist)
                    and _words(provider) & coll_words and not any(t in kind for t in _COPY_TYPES)):
                found[it["id"]] = it
        time.sleep(0.2)
    return list(found.values())[:MAX_VIEWS]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-artist", type=int, default=2, help="indexed works per artist (default 2)")
    parser.add_argument("--group-out", default=str(GROUP_OUT))
    parser.add_argument("--queries-out", default=str(QUERIES_OUT))
    parser.add_argument("--dry-run", action="store_true", help="first 3 artists, print only")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        sys.exit("EUROPEANA_API_KEY is not set")
    from evaluate import ARTIST_SEEDS  # the paper's artists

    artists = ARTIST_SEEDS[:3] if args.dry_run else ARTIST_SEEDS
    group, positives, negatives = [], [], []
    for artist in artists:
        try:
            works = wikidata_works(artist)
        except Exception as e:
            log.warning("%s: Wikidata failed (%s)", artist, e)
            continue
        indexed = 0
        for work in works:
            views = europeana_views(work, artist, api_key) if indexed < args.per_artist else []
            entry = {"artist": artist, "work": work["name"] or work["titles"][0], "wikidata": work["wikidata"],
                     "image_url": work["image"] + "?width=1024"}
            if views:
                indexed += 1
                oid = f"{re.sub(r'[^a-z]+', '_', artist.lower()).strip('_')}_{work['wikidata']}"
                group.append({
                    "object_id": oid, "name": entry["work"], "typology": "artwork", "status": "auto_collection_match",
                    "object_source": "Europeana", "europeana_ids": ";".join(v["id"] for v in views),
                    "object_title": (views[0].get("title") or [""])[0], "object_url": item_url(views[0]["id"]),
                    "n_views": len(views), "rights": ";".join(dict.fromkeys((v.get("rights") or [""])[0] for v in views)),
                    "data_providers": ";".join(dict.fromkeys(v.get("dataProvider", [""])[0] for v in views)),
                    "arco_site_id": "", "artist": artist, "collection": work["collections"][0],
                    "wikidata": work["wikidata"], "note": "",
                })
                positives.append(dict(entry, expected_object_id=oid))
            elif indexed:  # a famous work of an artist already in the index: hard negative
                negatives.append(dict(entry, expected_object_id=""))
        log.info("%-28s %d indexed / %d works", artist, indexed, len(works))
        time.sleep(1.0)

    # Each photo gets one question in rotation; false premise names another indexed artist
    other = sorted({g["artist"] for g in group})
    rows = [dict(p, set="F0", augment="") for p in positives]
    rows += [dict(p, set=f"F0_{a}", augment=a) for p in positives for a in AUGMENTS]
    rows += [dict(n, set="F2", augment="") for n in negatives]
    for i, r in enumerate(rows):
        k = i % len(QUESTION_TEMPLATES)
        wrong = next((a for a in other[i % max(len(other), 1):] + other if a != r["artist"]), "Caravaggio")
        r.update(query_id=f"q{i:04d}", q_label=Q_LABELS[k], question=QUESTION_TEMPLATES[k].format(wrong_artist=wrong),
                 premise=f"opera di {wrong}" if Q_LABELS[k] == "false_premise" else "",
                 premise_false=int(Q_LABELS[k] == "false_premise"))

    log.info("group: %d works from %d artists; queries: %d (%d negatives)",
             len(group), len(other), len(rows), len(negatives))
    if args.dry_run:
        for g in group:
            log.info("  %s | %s | %s", g["name"], g["data_providers"], g["europeana_ids"])
        return
    for path, fields, data in ((args.group_out, GROUP_FIELDS, group), (args.queries_out, QUERY_FIELDS, rows)):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
        log.info("wrote %s", path)


if __name__ == "__main__":
    main()
