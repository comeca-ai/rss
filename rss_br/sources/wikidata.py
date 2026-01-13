from __future__ import annotations

from typing import Any

import httpx

from rss_br.sources import SourceSite


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"


def _sparql_newspapers_query(limit: int, offset: int) -> str:
    # Q11032 = newspaper, Q155 = Brazil, P856 = official website
    return f"""
SELECT ?item ?itemLabel ?site WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q11032 .
  ?item wdt:P17 wd:Q155 .
  ?item wdt:P856 ?site .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}
LIMIT {limit}
OFFSET {offset}
""".strip()


def fetch_newspapers(
    client: httpx.Client,
    *,
    max_sites: int | None = None,
    page_size: int = 300,
) -> list[SourceSite]:
    """
    Busca jornais brasileiros via Wikidata (SPARQL).

    Retorna uma lista com (nome, site_url, source="wikidata").
    """
    sites: list[SourceSite] = []
    offset = 0

    while True:
        if max_sites is not None and len(sites) >= max_sites:
            return sites[:max_sites]

        q = _sparql_newspapers_query(page_size, offset)
        resp = client.get(
            WIKIDATA_SPARQL_URL,
            params={"format": "json", "query": q},
            headers={"Accept": "application/sparql-results+json"},
        )
        resp.raise_for_status()

        data: dict[str, Any] = resp.json()
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            break

        for b in bindings:
            name = (b.get("itemLabel", {}) or {}).get("value")
            site = (b.get("site", {}) or {}).get("value")
            if not name or not site:
                continue
            sites.append(SourceSite(name=name.strip(), site_url=site.strip(), source="wikidata"))

        offset += page_size

    if max_sites is not None:
        return sites[:max_sites]
    return sites

