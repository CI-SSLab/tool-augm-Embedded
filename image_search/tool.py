import csv
import json

import cv2
import numpy as np
from PIL import Image

from image_search import index, search
from sources.arco import underwater_records
from sources.europeana import fetch_by_ids, item_url

# Last call kept for the Streamlit "execution details" panel. Scores and thumbnails
# stay here and never reach the LLM. Global state = single user, fine for the prototype.
_LAST_TRACE = {"decision": "", "ranked": [], "result": ""}

# The encoder takes 1.35 GB of VRAM: load it once per process
_ENCODER = None
_INDEX = None


def get_last_image_trace() -> dict:
    return dict(_LAST_TRACE)


# ----- COLOUR CORRECTION -----

def correct_colour(img: Image.Image, mode: str = "none") -> Image.Image:
    # Classic corrections only, no learned methods: none / grayworld / clahe (grayworld + CLAHE on L)
    if mode == "none":
        return img
    rgb = np.asarray(img, dtype=np.float32)
    # Gray-world: scale each channel so its mean matches the global mean (removes the blue-green cast)
    rgb = np.clip(rgb * (rgb.mean() / (rgb.mean(axis=(0, 1)) + 1e-6)), 0, 255).astype(np.uint8)
    if mode == "clahe":
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        lab[..., 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[..., 0])
        rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    elif mode != "grayworld":
        raise ValueError(f"unknown colour mode: {mode}")
    return Image.fromarray(rgb)


# ----- RECORDS BY ID -----

def _first(value):
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("def") or next(iter(value.values()), "")
    return value or ""


def _europeana_candidate(item: dict) -> dict:
    # Prefer the English description when the provider gives one; keep it short for the prompt
    lang = item.get("dcDescriptionLangAware") or {}
    description = _first(lang.get("en")) or _first(item.get("dcDescription"))
    # Europeana "year" is often missing; the DAI records carry the dating in edmTimespanLabel
    year = _first(item.get("year")) or "; ".join(_first(t) for t in item.get("edmTimespanLabel", []))
    return {
        "title": _first(item.get("title")) or "(senza titolo)",
        "creator": _first(item.get("dcCreator")),
        "year": year,
        "url": item_url(item["id"]),
        "source": "Europeana",
        "description": description[:400],
        # Place recorded by the provider: it may be the findspot or the museum, the record does not say which
        "place": ", ".join(_first(p) for p in item.get("edmPlaceLabel", [])),
        "current_location": "",
        "site": None,
    }


def _iccd_record(rec: dict) -> dict:
    return {
        "title": rec["title"], "creator": "", "year": rec["date"], "url": rec["url"], "source": "ICCD",
        "description": rec["description"][:400], "place": rec["address"],
        "current_location": rec["location"],
    }


def _site_block(rec: dict) -> dict:
    return {"title": rec["title"], "url": rec["url"], "source": "ICCD", "chronology": rec["date"],
            "address": rec["address"]}


def _candidates(object_ids: list, group: dict) -> tuple:
    # One Europeana call for all object IDs, one cached ArCo query for the sites
    rows = [group[o] for o in object_ids]
    eids = [e for r in rows for e in r["europeana_ids"].split(";")[:1] if e]
    error = None
    try:
        items = fetch_by_ids(eids) if eids else {}
    except Exception as e:
        items, error = {}, f"Europeana non disponibile: {e}"
    try:
        sites = {r["id"]: r for r in underwater_records()}
    except Exception as e:
        sites, error = {}, f"ICCD non disponibile: {e}"

    out = []
    for r in rows:
        site = sites.get(r["arco_site_id"])
        eid = r["europeana_ids"].split(";")[0]
        if eid:
            if eid not in items:
                continue
            cand = _europeana_candidate(items[eid])
            # The object -> site link is a hand-made table: pass it only once someone checked it
            if site and r["status"] == "verified":
                cand["site"] = _site_block(site)
        elif site:
            # In-situ structure: the ICCD record is both the object and the site
            cand = dict(_iccd_record(site), site=None)
        else:
            continue
        out.append(cand)
    return out, error


# ----- TOOL -----

def _payload(decision: str, candidates: list = None, error: str = None) -> str:
    return json.dumps({"decision": decision, "candidates": candidates or [], "error": error},
                      ensure_ascii=False, indent=2)


def image_search(photo, colour: str = "none", budget: int = 280) -> str:
    # photo is a path or a PIL image. Returns the JSON for the LLM: no scores, no image
    global _ENCODER, _INDEX
    from image_search.encoder import Encoder, load_image

    if _ENCODER is None:
        _ENCODER = Encoder(budget=budget)
        _INDEX = index.load_index(index.index_dir(_ENCODER.slug, index.group_csv()))
    emb, rows = _INDEX
    group = {g["object_id"]: g for g in csv.DictReader(open(index.group_csv(), encoding="utf-8"))}

    img = photo if isinstance(photo, Image.Image) else load_image(photo)
    ranked = search.rank_objects(_ENCODER.embed([correct_colour(img, colour)])[0], emb, rows)
    decision, ids = search.decide(ranked)

    if decision == "no_match":
        result = _payload(decision, error="no_match_in_curated_group")
    else:
        candidates, error = _candidates(ids, group)
        result = _payload(decision if candidates else "no_match", candidates, error)

    _LAST_TRACE.update(decision=decision, result=result,
                       ranked=[{"object_id": o, "score": s, "image_url": rows[i]["image_url"]}
                               for o, s, i in ranked[:5]])
    return result


if __name__ == "__main__":  # self-check of the parts that need no GPU nor network
    flat = Image.new("RGB", (8, 8), (20, 120, 140))
    px = np.asarray(correct_colour(flat, "grayworld"), dtype=int)[0, 0]
    assert px.max() - px.min() <= 1, px  # uniform cast -> gray
    assert correct_colour(flat, "clahe").size == flat.size
    item = {"id": "/1/x", "title": ["T"], "edmTimespanLabel": [{"def": "um 45"}],
            "dcDescriptionLangAware": {"de": ["d"], "en": ["e"]}, "edmPlaceLabel": [{"def": "Baia"}]}
    c = _europeana_candidate(item)
    assert (c["year"], c["description"], c["place"]) == ("um 45", "e", "Baia")
    assert c["url"].endswith("/item/1/x")
    print("tool.py self-check ok")
