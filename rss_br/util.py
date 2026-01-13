from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


def normalize_site_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    p = urlparse(url)
    scheme = p.scheme.lower() if p.scheme else "https"
    netloc = p.netloc
    path = p.path or "/"
    # remove fragments
    return urlunparse((scheme, netloc, path, "", p.query, ""))


def make_site_variants(url: str) -> list[str]:
    """
    Retorna variantes http/https para aumentar chance de resposta.
    """
    u = normalize_site_url(url)
    if not u:
        return []
    p = urlparse(u)
    https = urlunparse(("https", p.netloc, p.path or "/", "", p.query, ""))
    http = urlunparse(("http", p.netloc, p.path or "/", "", p.query, ""))
    if https == http:
        return [https]
    return [https, http]


def resolve_url(base: str, href: str) -> str:
    return urljoin(base, href)


def strip_fragment(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))


def dedupe_preserve_order(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

