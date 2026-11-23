"""Build the curated-group ground-truth CSV.

Candidates (object views + linked ArCo site) are listed by hand below; this
script only fetches metadata from the sources, so every value in the CSV is
traceable to Europeana or ICCD/ArCo. Status "to_verify" rows need a human check.

Usage: python eval/underwater/build_curated_group.py
"""
import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "census" / "curated_group.csv"
EUROPEANA = "https://api.europeana.eu/record/v2/search.json"
ARCO_RES = "https://w3id.org/arco/resource/ArchaeologicalProperty/"

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


def europeana_by_ids(api_key: str, ids: list) -> dict:
    # One batch call: europeana_id:("a" OR "b" ...)
    query = "europeana_id:(" + " OR ".join(f'"{i}"' for i in ids) + ")"
    r = requests.get(EUROPEANA, params={"wskey": api_key, "query": query, "rows": 100, "profile": "rich"}, timeout=30)
    r.raise_for_status()
    return {it["id"]: it for it in r.json().get("items", [])}


def arco_sites(site_ids: list) -> dict:
    values = " ".join(f"<{ARCO_RES}{s}>" for s in site_ids)
    q = f"""SELECT ?s (SAMPLE(?l) AS ?label) (SAMPLE(?d) AS ?date) (COUNT(DISTINCT ?img) AS ?imgs)
      WHERE {{ VALUES ?s {{ {values} }} ?s <http://www.w3.org/2000/01/rdf-schema#label> ?l .
      OPTIONAL {{ ?s <http://purl.org/dc/elements/1.1/date> ?d }}
      OPTIONAL {{ ?s <http://xmlns.com/foaf/0.1/depiction> ?img }} }} GROUP BY ?s"""
    r = requests.get(os.getenv("ARCO_SPARQL_URL", "http://dati.beniculturali.it/sparql"),
                     params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=120)
    r.raise_for_status()
    out = {}
    for b in r.json()["results"]["bindings"]:
        sid = b["s"]["value"].rsplit("/", 1)[-1]
        out[sid] = {k: b.get(k, {}).get("value", "") for k in ("label", "date", "imgs")}
    return out


def main():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        raise SystemExit("EUROPEANA_API_KEY missing in .env")

    all_ids = [i for c in CANDIDATES for i in c[3]]
    records = europeana_by_ids(api_key, all_ids)
    missing = [i for i in all_ids if i not in records]
    sites = arco_sites(sorted({c[4] for c in CANDIDATES if c[4]}))

    rows = []
    for obj_id, name, typology, ids, site, status, note in CANDIDATES:
        recs = [records[i] for i in ids if i in records]
        s = sites.get(site, {})
        rows.append({
            "object_id": obj_id, "name": name, "typology": typology, "status": status,
            "object_source": "Europeana" if ids else "ICCD",
            "europeana_ids": ";".join(ids),
            "object_title": (recs[0].get("title") or [""])[0] if recs else "",
            "object_url": f"https://www.europeana.eu/it/item{ids[0]}" if ids else "",
            "n_views": len(recs) if ids else int(s.get("imgs") or 0),
            "n_previews": sum(1 for r in recs if r.get("edmPreview")) if ids else int(s.get("imgs") or 0),
            "rights": ";".join(sorted({(r.get("rights") or [""])[0] for r in recs})),
            "data_providers": ";".join(sorted({(r.get("dataProvider") or [""])[0] for r in recs})),
            "arco_site_id": site, "site_label": s.get("label", ""), "site_dating": s.get("date", ""),
            "site_url": f"https://catalogo.beniculturali.it/detail/ArchaeologicalProperty/{site}" if site else "",
            "note": note,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT} ({len(rows)} objects); Europeana ids found {len(all_ids) - len(missing)}/{len(all_ids)}")
    for m in missing:
        print("  MISSING on Europeana:", m)
    for site in {c[4] for c in CANDIDATES if c[4]} - set(sites):
        print("  MISSING on ArCo:", site)


if __name__ == "__main__":
    main()
