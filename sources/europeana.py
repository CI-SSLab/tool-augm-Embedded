"""Europeana Search API: read records by ID."""
import os

import requests

SEARCH_URL = "https://api.europeana.eu/record/v2/search.json"
PAGE = 100  # max rows per Search API call


def item_url(europeana_id: str) -> str:
    return f"https://www.europeana.eu/it/item{europeana_id}"


def fetch_by_ids(ids: list, api_key: str = None, profile: str = "rich", timeout: int = 30) -> dict:
    """Return {europeana_id: item} using one call per 100 IDs: query=europeana_id:("a" OR "b" ...)."""
    api_key = api_key or os.getenv("EUROPEANA_API_KEY")
    if not api_key:
        raise RuntimeError("EUROPEANA_API_KEY is not set")
    ids = list(dict.fromkeys(ids))
    out = {}
    for start in range(0, len(ids), PAGE):
        chunk = ids[start:start + PAGE]
        query = "europeana_id:(" + " OR ".join(f'"{i}"' for i in chunk) + ")"
        r = requests.get(SEARCH_URL, params={"wskey": api_key, "query": query, "rows": len(chunk), "profile": profile},
                         timeout=timeout)
        r.raise_for_status()
        out.update({it["id"]: it for it in r.json().get("items", [])})
    return out
