"""Download the demo photos listed in data/demo/demo_photos.csv into data/demo/photos/.

Only Commons photos with an open licence (CC0, CC BY, CC BY-SA, public domain) are listed;
the slides must credit author and licence as given in the CSV.

Usage:
    python scripts/demo/fetch_demo_photos.py
"""
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from image_search.index import cached_image  # noqa: E402

LIST = ROOT / "data" / "demo" / "demo_photos.csv"
OUT = ROOT / "data" / "demo" / "photos"

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for row in csv.DictReader(open(LIST, encoding="utf-8")):
        dest = OUT / f"{row['demo_id']}.jpg"
        shutil.copy(cached_image(row["image_url"]), dest)
        print(f"{dest.name:28} {row['license']:14} {row['author'][:60]}")
