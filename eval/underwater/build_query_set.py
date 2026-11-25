"""Build the underwater image test set (photo + question) from Wikimedia Commons.

Each Commons category is mapped by hand below to a condition and, when it shows an
indexed object, to its object_id. Files in mixed categories get the object from their
file name (rules below) or stay "to_label". Every label is provisional: label_status says
where it comes from, and a human check is required before the numbers are final
(captions online are often wrong). The repo stores URLs and licences only, no images.

  C0  museum photo of an indexed object       (in-domain upper bound)
  C1  underwater photo of an indexed object   (main condition)
  C2  hard negative: other underwater sites, statues not indexed, empty seabed
  split = val for about 1 photo in 5 of C1/C2 (tau/delta tuning only), test otherwise

Usage:
    python eval/underwater/build_query_set.py [--out data/eval/underwater_queries.csv] [--dry-run]
"""
import argparse
import csv
import logging
import re
import sys
import time
import zlib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "eval" / "underwater_queries.csv"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "heritage-image-eval/0.1 (research prototype)"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
# category, set, expected object ("rules" = from the file name), domain, subcategory depth, max files
CATEGORIES = [
    ("Emperor Claudius' sunken nymphaeum", "C1", "rules:site_punta_epitaffio", "underwater", 1, 80),
    ("Underwater Archaeological Park of Baiae", "C1", "rules:", "underwater", 0, 80),
    ("Portus Julius", "C2", "", "underwater", 0, 40),
    # Numbered museum photos may show the Ninfeo originals: only named files get a label
    ("Museo archeologico dei Campi Flegrei (Baia)", "C0", "rules:", "museum", 1, 80),
    ("God of Cape Artemision", "C0", "artemision_god", "museum", 1, 25),
    ("Artemision jockey", "C0", "artemision_jockey", "museum", 1, 25),
    ("Antikythera Ephebe (NAMA x13396)", "C0", "antikythera_ephebe", "museum", 1, 25),
    ("Antikythera philosopher in the National Archaeological Museum of Athens", "C0", "antikythera_philosopher",
     "museum", 1, 25),
    ("Riace bronzes", "C2", "", "museum", 1, 20),
    ("Dancing Satyr of Mazara del Vallo", "C2", "", "museum", 0, 15),
    ("Christ of the Abyss", "C2", "", "underwater", 0, 15),
    ("Archaeological site of Pavlopetri", "C2", "", "underwater", 0, 20),
    ("Museo nazionale di archeologia subacquea (Grado)", "C2", "", "museum", 0, 15),
    ("Olous (Elounda)", "C2", "", "underwater", 0, 10),
]

# File-name rules for mixed categories, first match wins ("companion of Ulysses" before "Ulysses")
NAME_RULES = [
    # Baios is one of the Ninfeo statues but not one of the indexed records
    (r"baios|bajos", "to_label"),
    (r"otre|wineskin|compagno|companion", "baia_odysseus_companion"),
    (r"ulisse|odisseo|odysseus|ulysses|ulixes", "baia_odysseus"),
    (r"dionis|dionys|bacco|bacchus", "baia_dionysos"),
    (r"antonia", "baia_antonia"),
    (r"epitaffio|ninfeo|nymphaeum", "site_punta_epitaffio"),
    (r"miseno|misenum", "site_miseno_porto"),
    (r"portus.?julius|portus.?iulius", "negative"),
    # Vases and inscriptions in the Baia museum are clearly not indexed objects
    (r"painter|\bARV\b|\bCIL\b|EDCS|inschrift|inscription", "negative"),
]
# Plans, maps and drawings are not photos
SKIP = re.compile(r"\b(plan|pianta|map|mappa|planimetria|rilievo|drawing|disegno)\b|\.(svg|png|pdf|tif)$", re.I)

QUESTION_TEMPLATES = ["Cos'è?", "A che epoca risale?", "Da quale sito proviene?", "Viene da Pompei?"]
Q_LABELS = ["identification", "temporal", "provenance", "false_premise"]

FIELDS = ["query_id", "set", "split", "expected_object_id", "label_status", "domain", "work", "image_url",
          "page_url", "license", "author", "category", "augment", "q_label", "question", "premise", "premise_false"]


def _api(**params) -> dict:
    # Commons answers rate limits with an HTML page: back off and retry
    for attempt in range(5):
        r = requests.get(API, params=dict(params, format="json"), headers=HEADERS, timeout=60)
        if r.ok and r.headers.get("Content-Type", "").startswith("application/json"):
            return r.json()
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    raise RuntimeError("Commons API did not return JSON")


def category_files(category: str, depth: int) -> list:
    # File titles of a category and of its subcategories down to depth
    files, todo, seen = [], [(category, 0)], set()
    while todo:
        cat, d = todo.pop(0)
        if cat in seen:
            continue
        seen.add(cat)
        cont = {}
        while True:
            data = _api(action="query", list="categorymembers", cmtitle=f"Category:{cat}", cmlimit=500, **cont)
            for m in data["query"]["categorymembers"]:
                if m["ns"] == 6:
                    files.append((m["title"], cat))
                elif m["ns"] == 14 and d < depth:
                    todo.append((m["title"][9:], d + 1))
            if "continue" not in data:
                break
            cont = data["continue"]
        time.sleep(1)
    return files


def image_info(titles: list) -> dict:
    # Thumbnail URL, licence and author for up to 50 files per call
    out = {}
    for i in range(0, len(titles), 50):
        data = _api(action="query", prop="imageinfo", titles="|".join(titles[i:i + 50]),
                    iiprop="url|extmetadata|mime", iiurlwidth=1024)
        for page in data["query"]["pages"].values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            out[page["title"]] = {
                "image_url": info.get("thumburl", ""), "page_url": info.get("descriptionurl", ""),
                "mime": info.get("mime", ""),
                "license": meta.get("LicenseShortName", {}).get("value", ""),
                "author": re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:120],
            }
        time.sleep(1)
    return out


def label(title: str, expected: str) -> tuple:
    # (expected_object_id, label_status) from the category mapping or the file-name rules
    if not expected.startswith("rules:"):
        return expected, "auto_category"
    for pattern, oid in NAME_RULES:
        if re.search(pattern, title, re.I):
            if oid == "to_label":
                return "", "to_label"
            return ("" if oid == "negative" else oid), "auto_filename"
    default = expected[6:]
    if default == "negative":
        return "", "auto_category"
    return (default, "auto_category") if default else ("", "to_label")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--dry-run", action="store_true", help="print counts only")
    args = parser.parse_args()

    rows, seen = [], set()
    for category, cond, expected, domain, depth, cap in CATEGORIES:
        files = [(t, c) for t, c in category_files(category, depth) if t not in seen and not SKIP.search(t)]
        files = files[:cap]
        info = image_info([t for t, _ in files])
        kept = 0
        for title, sub in files:
            meta = info.get(title, {})
            if not meta.get("image_url") or not meta["mime"].startswith("image/jpeg"):
                continue
            seen.add(title)
            oid, status = label(title, expected)
            # Indexed object: C0 or C1 by domain. Anything else is a negative, unless still to label
            if oid:
                row_set = "C0" if domain == "museum" else "C1"
            else:
                row_set = "unlabeled" if status == "to_label" else "C2"
            split = "val" if row_set in ("C1", "C2") and zlib.crc32(title.encode()) % 5 == 0 else "test"
            rows.append({"set": row_set, "split": split, "expected_object_id": oid, "label_status": status,
                         "domain": domain, "work": title[5:], "category": sub, "augment": "",
                         **{k: meta[k] for k in ("image_url", "page_url", "license", "author")}})
            kept += 1
        log.info("%-70s %3d files", category[:70], kept)

    for i, r in enumerate(rows):
        k = i % len(QUESTION_TEMPLATES)
        r.update(query_id=f"u{i:04d}", q_label=Q_LABELS[k], question=QUESTION_TEMPLATES[k],
                 premise="Pompei" if Q_LABELS[k] == "false_premise" else "", premise_false=int(k == 3))

    counts = {}
    for r in rows:
        key = (r["set"], r["split"], r["label_status"])
        counts[key] = counts.get(key, 0) + 1
    for key, n in sorted(counts.items()):
        log.info("  %-3s %-5s %-14s %d", *key, n)
    if args.dry_run:
        return
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %s (%d rows)", args.out, len(rows))


if __name__ == "__main__":
    main()
