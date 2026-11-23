"""Build the curated-group ground-truth CSV.

Candidates (object views + linked ArCo site) are listed by hand below; this
script only fetches metadata from the sources, so every value in the CSV is
traceable to Europeana or ICCD/ArCo. Status "to_verify" rows need a human check.
Same layout as evaluation/evaluate.py: candidates as a module constant, main()
with --out / --dry-run, CSV output.

Usage:
    python eval/underwater/build_curated_group.py [--out data/census/curated_group.csv] [--dry-run]
"""
import argparse
import csv
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sources.arco import fetch_sites  # noqa: E402
from sources.europeana import fetch_by_ids, item_url  # noqa: E402

OUT = ROOT / "data" / "census" / "curated_group.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

PUNTA_EPITAFFIO = "1500910318"

# object_id, name, typology, europeana view ids, ArCo site id (or "" if none), status, note
CANDIDATES = [
    ("baia_odysseus", "Ulisse (gruppo della Weinreichung), Ninfeo di Punta Epitaffio", "museum_object",
     ["/2020707/https___arachne_dainst_org_entity_1105879"], PUNTA_EPITAFFIO, "to_verify",
     "Europeana place=Baia (not Punta Epitaffio): site link is manual, confirm; head exposed to sea water"),
    ("baia_odysseus_companion", "Compagno di Ulisse con otre, Ninfeo di Punta Epitaffio", "museum_object",
     ["/2020707/https___arachne_dainst_org_entity_1105880"], PUNTA_EPITAFFIO, "to_verify",
     "Europeana place=Baia (not Punta Epitaffio): site link is manual, confirm"),
    ("baia_dionysos", "Dioniso con corona d'edera", "museum_object",
     ["/199/item_7MO566HZPHI34YENGXTEZBTHQMJVZ6JM"], PUNTA_EPITAFFIO, "to_verify",
     "Marburg record has no place: check Baia provenance on bildindex.de (obj20243333)"),
    ("baia_antonia", "Statua ritratto di Antonia Augusta", "museum_object",
     ["/199/item_QSZPZISMDOUBVYSMMTLAK5Y2BE4YEWGF"], PUNTA_EPITAFFIO, "to_verify",
     "Marburg record has no place: check Baia provenance on bildindex.de (obj20243334)"),
    ("artemision_god", "Zeus/Poseidon di Capo Artemisio", "museum_object",
     ["/2020707/https___arachne_dainst_org_entity_1101564", "/199/item_6ZLQGMQRYUZ2J5BAGRS7UPVHL2BJWUVX",
      "/626/item_JXGKES7CTHEHPC5JYNDN7GRHYJUFOHCM", "/626/item_XIZKZJL5WQBIXT5J6FZJ7PS4PWDNQ4Z2",
      "/626/item_FWBVT4MS5EDLPPDYWFHMKCLMUUO2FJAN", "/737/item_Y6RKQ4F3VM5Y43GYV7W3DVMCGWLRT5SL",
      "/188/item_GP5O6HJKGPYL346EBPTA4YG6TSKD4BUA", "/463/item_SVHXPSHUPQFT3J4LRNBHXH2XOARR3P7K",
      "/437/item_BVJ6IXZ3GNCO7C27Z7U26ABCS2F75MX6", "/440/item_YYHTILNGTCRP2O25NP4IRRYYJPYN3FNK",
      "/440/item_KAH4EZAMOPJN2QEBWLLFCRCKCEF4NH4L", "/437/item_GIDFMN2OCVXSKPT4HL2KHCMRQUFYTEMN",
      "/463/item_WSDVZAUHIFIJ7REUOTIAGJIQ7XODRAZL"], "", "to_verify",
     "find site in Greece: no ArCo card -> graceful degradation for the site; shipwreck cargo: inclusion still open"),
    ("artemision_jockey", "Fantino di Capo Artemisio", "museum_object",
     ["/2020707/https___arachne_dainst_org_entity_1061321", "/199/item_L5ZT64BU5TVW4HO3NNZBRC2RAAEJXWS4",
      "/199/item_GOT4UACS3BTVYCUBBKJR5EIHANMTRUAJ", "/440/item_X6XCZNRWF3ARM6D2EM575UC3Z3KNKXNP",
      "/188/item_2DESXCCL2HAV7PXH3MYW2ATC4WTWSHP3"], "", "to_verify",
     "find site in Greece: no ArCo card; shipwreck cargo: inclusion still open"),
    ("antikythera_ephebe", "Efebo di Anticitera", "museum_object",
     ["/2020707/https___arachne_dainst_org_entity_1061322",
      "/122/https___www_searchculture_gr_aggregator_edm_ELIA_000100_22_465313",
      "/122/https___www_searchculture_gr_aggregator_edm_ELIA_000100_22_593184",
      "/122/https___www_searchculture_gr_aggregator_edm_ELIA_000100_22_463955",
      "/199/item_4EH5COOWNSP2U37Q5WXHZOLNI2S2ANR7", "/188/item_3LDCIS6BRMZ4CMF3Q7VXMIH7SH4GD5UV",
      "/463/item_LZXP74777LVSTFV4PV4D6KZ2DYGF4TPG", "/440/item_WAHJUB7MVY2K4OXHXSILI57MI5NB6PLY",
      "/626/item_3LTIIV2F5RWW6BCDTFIY4QEFAXUFMF2X"], "", "to_verify",
     "find site in Greece: no ArCo card; shipwreck cargo: inclusion still open; some views CC BY (SearchCulture)"),
    ("antikythera_philosopher", "Filosofo di Anticitera", "museum_object",
     ["/626/item_D7PQIS7UXSXRNIGKXR4IALJDNIKT7VVR", "/199/item_BGJ7M477FEWITQQRHJFOVVRUTSVRBS4O"], "", "to_verify",
     "only 2 views; shipwreck cargo: inclusion still open"),
    # In-situ structures: the index photo is the ArCo site photo itself (no Europeana record)
    ("site_punta_epitaffio", "Ninfeo di Punta Epitaffio (strutture sommerse)", "in_situ_structure",
     [], PUNTA_EPITAFFIO, "verified", "catalogue photo is underwater (diver + draped statue)"),
    # Baia-area ARCHEOMAR cards 1500910307/14/16/17/20 only have maps or plans: not usable as index photos.
    # Replacements below have a real photo on the card (checked by eye).
    ("site_miseno_porto", "Porto di Miseno, scogliera foranea (bitta sommersa)", "in_situ_structure", [],
     "1500910313", "to_verify", "underwater photo of a bollard fragment; Bacoli, Campi Flegrei"),
    ("site_torre_scassata", "Torre Scassata, mosaico sommerso", "in_situ_structure", [],
     "1500910325", "to_verify", "B/W photo of a mosaic floor; underwater shot not certain"),
    ("site_porto_1500910310", "Infrastruttura portuale sommersa (Campania, III-I a.C.)", "in_situ_structure", [],
     "1500910310", "to_verify", "underwater photo; check locality (outside Baia)"),
    ("site_vasche_1800177710", "Vasche scavate nella roccia (Calabria)", "in_situ_structure", [],
     "1800177710", "to_verify", "5 photos, partly submerged rock-cut tanks"),
]


def parse_args():
    p = argparse.ArgumentParser(description="Build the curated-group ground-truth CSV")
    p.add_argument("--out", type=str, default=str(OUT))
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    if args.dry_run:
        for obj_id, name, typology, ids, site, status, _ in CANDIDATES:
            print(f"  {obj_id:26} {typology:18} views={len(ids):>2} site={site or '-':10} {status}")
        return

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        raise SystemExit("EUROPEANA_API_KEY missing in .env")

    all_ids = [i for c in CANDIDATES for i in c[3]]
    records = fetch_by_ids(all_ids, api_key)
    missing = [i for i in all_ids if i not in records]
    sites = fetch_sites(sorted({c[4] for c in CANDIDATES if c[4]}))

    rows = []
    for obj_id, name, typology, ids, site, status, note in CANDIDATES:
        recs = [records[i] for i in ids if i in records]
        s = sites.get(site, {})
        rows.append({
            "object_id": obj_id, "name": name, "typology": typology, "status": status,
            "object_source": "Europeana" if ids else "ICCD",
            "europeana_ids": ";".join(ids),
            "object_title": (recs[0].get("title") or [""])[0] if recs else "",
            "object_url": item_url(ids[0]) if ids else "",
            "n_views": len(recs) if ids else len(s.get("images", [])),
            "n_previews": sum(1 for r in recs if r.get("edmPreview")) if ids else len(s.get("images", [])),
            "rights": ";".join(sorted({(r.get("rights") or [""])[0] for r in recs})),
            "data_providers": ";".join(sorted({(r.get("dataProvider") or [""])[0] for r in recs})),
            "arco_site_id": site, "site_label": s.get("title", ""), "site_dating": s.get("date", ""),
            "site_url": s.get("url", ""),
            "note": note,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    log.info("CSV saved -> %s  (%d objects); Europeana ids found %d/%d",
             out, len(rows), len(all_ids) - len(missing), len(all_ids))
    for m in missing:
        log.warning("  MISSING on Europeana: %s", m)
    for site in {c[4] for c in CANDIDATES if c[4]} - set(sites):
        log.warning("  MISSING on ArCo: %s", site)


if __name__ == "__main__":
    main()
