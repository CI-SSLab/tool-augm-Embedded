"""ICCD / ArCo knowledge graph: read archaeological site records by ID."""
import os

import requests

RESOURCE = "https://w3id.org/arco/resource/ArchaeologicalProperty/"
CATALOGUE_URL = "https://catalogo.beniculturali.it/detail/ArchaeologicalProperty/"
DEFAULT_ENDPOINT = "http://dati.beniculturali.it/sparql"
SEP = "|||"


def site_url(arco_id: str) -> str:
    return CATALOGUE_URL + arco_id


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
    r = requests.get(os.getenv("ARCO_SPARQL_URL") or DEFAULT_ENDPOINT, params={"query": query},
                     headers={"Accept": "application/sparql-results+json"}, timeout=timeout)
    r.raise_for_status()
    out = {}
    for b in r.json()["results"]["bindings"]:
        arco_id = b["s"]["value"].rsplit("/", 1)[-1]
        get = lambda k: b.get(k, {}).get("value", "")  # noqa: E731
        out[arco_id] = {
            "title": get("title"), "date": get("date"), "description": get("description"),
            "images": [u for u in get("images").split(SEP) if u], "url": site_url(arco_id),
        }
    return out
