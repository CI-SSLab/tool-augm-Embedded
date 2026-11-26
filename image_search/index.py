"""Vector index of catalogue photos for the curated group.

On disk (one folder per encoder): embeddings.npy (N x dim, L2-normalised) and
rows.csv (row -> object_id, source, view_id, image_url, license). Images are
cached in data/index_images/ (gitignored: most are In Copyright).
"""
import csv
import hashlib
import os
from pathlib import Path

import numpy as np
import requests

from sources.arco import fetch_sites
from sources.europeana import fetch_by_ids

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data" / "census"
CACHE = ROOT / "data" / "index_images"
INDEX_ROOT = ROOT / "data" / "index"
ROW_FIELDS = ["object_id", "source", "view_id", "image_url", "license"]


def group_csv() -> Path:
    # IMAGE_GROUP picks the object group: curated_group (underwater, default) or famous_group (paintings test)
    return CENSUS / f"{os.getenv('IMAGE_GROUP') or 'curated_group'}.csv"


def list_views(group_csv: Path) -> list:
    """One dict per catalogue photo: Europeana previews for objects, ICCD photos for in-situ sites."""
    group = list(csv.DictReader(open(group_csv, encoding="utf-8")))
    records = fetch_by_ids([i for g in group for i in g["europeana_ids"].split(";") if i])
    sites = fetch_sites([g["arco_site_id"] for g in group if not g["europeana_ids"]])
    views = []
    for g in group:
        for eid in filter(None, g["europeana_ids"].split(";")):
            item = records.get(eid, {})
            if item.get("edmPreview"):
                views.append({"object_id": g["object_id"], "source": "Europeana", "view_id": eid,
                              "image_url": item["edmPreview"][0], "license": (item.get("rights") or [""])[0]})
        if not g["europeana_ids"]:
            for n, url in enumerate(sites.get(g["arco_site_id"], {}).get("images", [])):
                # shortcut: ICCD photo licence is not in ArCo data, left empty; fill in by hand when known
                views.append({"object_id": g["object_id"], "source": "ICCD", "view_id": f"{g['arco_site_id']}#{n}",
                              "image_url": url, "license": ""})
    # Optional reference views that are not catalogue photos (e.g. underwater photos from Commons):
    # <group>_extra_views.csv, used only by the groups that have one
    extra = group_csv.with_name(f"{group_csv.stem}_extra_views.csv")
    if extra.exists():
        views += [{k: r[k] for k in ROW_FIELDS} for r in csv.DictReader(open(extra, encoding="utf-8"))]
    return views


def cached_image(url: str) -> Path:
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if not path.exists():
        # Wikimedia refuses requests without a descriptive User-Agent
        r = requests.get(url, timeout=60, headers={"User-Agent": "heritage-image-eval/0.1 (research prototype)"})
        r.raise_for_status()
        if not r.headers.get("Content-Type", "").startswith("image/"):
            raise ValueError(f"not an image: {r.headers.get('Content-Type')}")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path


def index_dir(encoder_slug: str, group: Path) -> Path:
    # One index per group and encoder; the underwater group keeps its original folder
    return INDEX_ROOT / (encoder_slug if group.stem == "curated_group" else f"{group.stem}_{encoder_slug}")


def load_index(folder: Path):
    emb = np.load(folder / "embeddings.npy")
    rows = list(csv.DictReader(open(folder / "rows.csv", encoding="utf-8")))
    assert len(rows) == emb.shape[0], "rows.csv and embeddings.npy are out of sync"
    return emb, rows


def build(encoder, group_csv: Path) -> Path:
    """Incremental build: reuse embeddings of views already indexed, embed only new ones,
    drop views no longer in the group."""
    from image_search.encoder import load_image

    folder = index_dir(encoder.slug, group_csv)
    old = {}
    if (folder / "embeddings.npy").exists():
        emb, rows = load_index(folder)
        old = {(r["object_id"], r["view_id"]): emb[i] for i, r in enumerate(rows)}

    views, vectors, todo = [], [], []
    for v in list_views(group_csv):
        key = (v["object_id"], v["view_id"])
        if key in old:
            views.append(v)
            vectors.append(old[key])
            continue
        try:
            todo.append((v, load_image(cached_image(v["image_url"]))))
        except Exception as e:  # one broken thumbnail must not stop the build
            print(f"  skip {v['object_id']} {v['view_id']}: {e}")

    if todo:
        new = encoder.embed([im for _, im in todo])
        views += [v for v, _ in todo]
        vectors += list(new)

    folder.mkdir(parents=True, exist_ok=True)
    np.save(folder / "embeddings.npy", np.stack(vectors).astype(np.float32))
    with open(folder / "rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        w.writeheader()
        w.writerows({k: v[k] for k in ROW_FIELDS} for v in views)
    print(f"index {folder}: {len(views)} views ({len(todo)} new), "
          f"{len({v['object_id'] for v in views})} objects")
    return folder
