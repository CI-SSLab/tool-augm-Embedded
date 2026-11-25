"""ICCD / ArCo knowledge graph: read archaeological site records by ID, and the
text-path stage 4 (underwater sites, behind ENABLE_ICCD_FALLBACK)."""
import os
import re

import requests

RESOURCE = "https://w3id.org/arco/resource/ArchaeologicalProperty/"
CATALOGUE_URL = "https://catalogo.beniculturali.it/detail/ArchaeologicalProperty/"
DEFAULT_ENDPOINT = "http://dati.beniculturali.it/sparql"
SEP = "|||"


def site_url(arco_id: str) -> str:
    return CATALOGUE_URL + arco_id


def _sparql(query: str, timeout: int = 120) -> list:
    r = requests.get(os.getenv("ARCO_SPARQL_URL") or DEFAULT_ENDPOINT, params={"query": query},
                     headers={"Accept": "application/sparql-results+json"}, timeout=timeout)
    r.raise_for_status()
    return [{k: v.get("value", "") for k, v in b.items()} for b in r.json()["results"]["bindings"]]


def fetch_sites(ids: list, timeout: int = 120) -> dict:
    """Return {arco_id: {title, date, description, images, url}} with a single SPARQL query."""
    ids = [i for i in dict.fromkeys(ids) if i]
    if not ids:
        return {}
    values = " ".join(f"<{RESOURCE}{i}>" for i in ids)
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    SELECT ?s (SAMPLE(?l) AS ?title) (SAMPLE(?d) AS ?date) (SAMPLE(?desc) AS ?description)
           (GROUP_CONCAT(DISTINCT ?img; separator="{SEP}") AS ?images)
    WHERE {{
      VALUES ?s {{ {values} }}
      ?s rdfs:label ?l .
      OPTIONAL {{ ?s dc:date ?d }}
      OPTIONAL {{ ?s dc:description ?desc }}
      OPTIONAL {{ ?s foaf:depiction ?img }}
    }} GROUP BY ?s"""
    out = {}
    for b in _sparql(query, timeout):
        arco_id = b["s"].rsplit("/", 1)[-1]
        out[arco_id] = {
            "title": b.get("title", ""), "date": b.get("date", ""), "description": b.get("description", ""),
            "images": [u for u in b.get("images", "").split(SEP) if u], "url": site_url(arco_id),
        }
    return out


# ----- Stage 4 of the text cascade: ICCD underwater sites -----

def iccd_fallback_enabled() -> bool:
    return os.getenv("ENABLE_ICCD_FALLBACK", "").strip().lower() in ("1", "true", "yes")


_UNDERWATER = []  # in-memory cache, like the Europeana tool's


def underwater_records() -> list:
    """All ArCo records with underwater context (68 in Nov 2026), fetched once per process.
    Site names live in the location text, not in the label, and location nodes are shared by
    unrelated records: keep only location nodes whose URI carries the record's own ID."""
    if not _UNDERWATER:
        query = f"""
        PREFIX loc: <https://w3id.org/arco/ontology/location/>
        PREFIX core: <https://w3id.org/arco/ontology/core/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        SELECT ?s (SAMPLE(?l) AS ?title) (SAMPLE(?d) AS ?date) (SAMPLE(?desc) AS ?description)
               (GROUP_CONCAT(DISTINCT ?ld; separator=" | ") AS ?location) (SAMPLE(?al) AS ?address)
        WHERE {{
          ?s loc:hasTypeOfContext loc:UnderwaterContext ; rdfs:label ?l .
          OPTIONAL {{ ?s dc:date ?d }}
          OPTIONAL {{ ?s core:description ?desc }}
          OPTIONAL {{ ?s loc:hasTimeIndexedTypedLocation ?t . ?t loc:locationDetails ?ld .
                     FILTER(CONTAINS(STR(?t), STRAFTER(STR(?s), "ArchaeologicalProperty/"))) }}
          OPTIONAL {{ ?s loc:hasCulturalPropertyAddress ?a . ?a rdfs:label ?al }}
        }} GROUP BY ?s"""
        for b in _sparql(query):
            arco_id = b["s"].rsplit("/", 1)[-1]
            _UNDERWATER.append({"id": arco_id, "title": b.get("title", ""), "date": b.get("date", ""),
                                "description": b.get("description", ""), "location": b.get("location", ""),
                                # "Italia, Campania, NA, Bacoli, nr": "nr" = not recorded
                                "address": re.sub(r",\s*nr$", "", b.get("address", "")),
                                "url": site_url(arco_id)})
    return _UNDERWATER


def match_records(name: str, records: list, limit: int = 5) -> list:
    """Records whose text contains the most of the name's proper nouns (capitalised words,
    or all words of 4+ letters if none is capitalised). No match -> []."""
    words = re.findall(r"[^\W\d_]{4,}", name or "")
    keys = [w for w in words if w[0].isupper()] or words
    scored = []
    for rec in records:
        text = " ".join((rec["title"], rec["description"], rec["location"]))
        hits = sum(1 for k in keys if re.search(rf"\b{re.escape(k)}\b", text, re.IGNORECASE))
        if hits:
            scored.append((hits, rec))
    best = max((h for h, _ in scored), default=0)
    return [r for h, r in scored if h == best][:limit]


def iccd_items(name: str) -> list:
    """Stage 4 items in the Europeana tool's format (+ source/description/location).
    Any ArCo failure returns [] so the paper's error path is unchanged."""
    try:
        recs = match_records(name, underwater_records())
    except Exception:
        return []
    return [{
        # The ", Sito: dd/mm/yyyy hh.mm.ss" in ARCHEOMAR labels is a cataloguing timestamp, not a date of the site
        "title": re.sub(r",? ?Sito: [\d/]+ [\d.]+", "", r["title"]).strip(" ,"),
        "creator": "", "year": r["date"], "url": r["url"], "source": "ICCD",
        "description": r["description"], "location": r["location"], "address": r["address"],
    } for r in recs]


if __name__ == "__main__":  # self-check of the matcher on hand-made records
    recs = [{"title": "giacimento subacqueo", "description": "ninfeo", "location": "Punta Epitaffio, strutture"},
            {"title": "porto", "description": "", "location": "scogliera foranea di Miseno"},
            {"title": "relitto", "description": "", "location": "Baia di Santa Caterina"}]
    assert [r["location"][:5] for r in match_records("Ulysses of Punta Epitaffio", recs)] == ["Punta"]
    assert match_records("Miseno harbour", recs)[0]["location"].endswith("Miseno")
    assert match_records("Antikythera Youth", recs) == []
    assert match_records("baia", recs)[0]["title"] == "relitto"
    print("arco.py self-check ok")
