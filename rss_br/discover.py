from __future__ import annotations

from dataclasses import replace
from typing import Iterable
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup
import httpx

from rss_br.models import FeedRecord, FeedKind
from rss_br.util import dedupe_preserve_order, resolve_url, strip_fragment


_FEED_MIME_HINTS = (
    "application/rss+xml",
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "application/x-rss+xml",
)


def _looks_like_feed_url(url: str) -> bool:
    u = url.lower()
    if any(x in u for x in ("facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "tiktok.com")):
        return False
    if u.endswith((".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".zip")):
        return False
    return True


def discover_candidates(site_url: str, html: str | None) -> list[str]:
    """
    Descobre possíveis feeds a partir do HTML e padrões comuns.
    """
    candidates: list[str] = []
    base = site_url

    if html:
        soup = BeautifulSoup(html, "lxml")

        # <link rel="alternate" type="application/rss+xml" href="...">
        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel") or []).lower()
            typ = (link.get("type") or "").lower()
            href = (link.get("href") or "").strip()
            if not href:
                continue
            if "alternate" in rel and ("rss" in typ or "atom" in typ or "xml" in typ):
                u = strip_fragment(resolve_url(base, href))
                if _looks_like_feed_url(u):
                    candidates.append(u)

        # fallback: anchors with rss/atom/feed hints
        for a in soup.find_all("a"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            text = (a.get_text(" ", strip=True) or "").lower()
            hint = href.lower() + " " + text
            if any(k in hint for k in ("rss", "atom", "feed", "xml")):
                u = strip_fragment(resolve_url(base, href))
                if _looks_like_feed_url(u):
                    candidates.append(u)

    # common paths (WordPress and generic)
    common_paths = [
        "/feed/",
        "/feed",
        "/rss",
        "/rss/",
        "/rss.xml",
        "/atom.xml",
        "/index.xml",
        "/feeds",
        "/feed/rss",
        "/feed/atom",
        "/?feed=rss",
        "/?feed=rss2",
        "/?feed=atom",
    ]
    for p in common_paths:
        candidates.append(strip_fragment(resolve_url(base, p)))

    # de-dupe while preserving order
    return dedupe_preserve_order(candidates)


def _infer_kind(parsed: feedparser.FeedParserDict) -> FeedKind:
    v = (parsed.get("version") or "").lower()
    if v.startswith("rss") or "rss" in v:
        return "rss"
    if v.startswith("atom") or "atom" in v:
        return "atom"
    # some feeds parse without version
    if parsed.get("feed") and parsed.get("entries") is not None:
        return "xml"
    return "unknown"


def _extract_topics(parsed: feedparser.FeedParserDict, max_topics: int = 50) -> list[str]:
    topics: list[str] = []
    entries = parsed.get("entries") or []
    for e in entries[:200]:
        tags = e.get("tags") or []
        for t in tags:
            term = (t.get("term") or t.get("label") or "").strip()
            if not term:
                continue
            topics.append(term)
            if len(topics) >= max_topics * 3:
                break
        if len(topics) >= max_topics * 3:
            break

    # normalize + unique
    norm: list[str] = []
    seen: set[str] = set()
    for t in topics:
        tt = " ".join(t.split())
        key = tt.casefold()
        if not tt or key in seen:
            continue
        seen.add(key)
        norm.append(tt)
        if len(norm) >= max_topics:
            break
    return norm


def validate_feed(client: httpx.Client, url: str) -> FeedRecord:
    rec = FeedRecord(url=url)
    try:
        r = client.get(url)
        rec = replace(rec, status_code=r.status_code)
        if r.status_code >= 400:
            return replace(rec, error=f"http {r.status_code}")

        content_type = (r.headers.get("content-type") or "").lower()
        body = r.content
        if not body or len(body) < 50:
            return replace(rec, error="empty/too small response")

        # If server returns HTML, feedparser might still parse, but it's usually noise.
        if "text/html" in content_type and not any(x in content_type for x in _FEED_MIME_HINTS):
            # quick sniff: if it doesn't start like xml, bail
            head = body.lstrip()[:50].lower()
            if not (head.startswith(b"<?xml") or b"<rss" in head or b"<feed" in head):
                return replace(rec, error="looks like html, not feed")

        parsed = feedparser.parse(body)
        kind = _infer_kind(parsed)
        if kind == "unknown" or (not parsed.get("feed") and not parsed.get("entries")):
            return replace(rec, error="not parseable as rss/atom")

        feed = parsed.get("feed") or {}
        title = (feed.get("title") or "").strip() or None
        link = (feed.get("link") or "").strip() or None
        lang = (feed.get("language") or "").strip() or None
        entries = len(parsed.get("entries") or [])
        topics = _extract_topics(parsed)
        rec = replace(
            rec,
            kind=kind,
            title=title,
            homepage=link,
            language=lang,
            entries=entries,
            topics=topics,
        )
        return rec
    except Exception as e:  # noqa: BLE001 - CLI tool: keep reason
        return replace(rec, error=f"{type(e).__name__}: {e}")


def pick_best_feeds(feeds: Iterable[FeedRecord], max_feeds: int = 5) -> list[FeedRecord]:
    """
    Ordena priorizando feeds que parsearam e têm mais entries.
    """
    good = [f for f in feeds if not f.error]
    good.sort(key=lambda f: (f.entries or 0), reverse=True)
    return good[:max_feeds]


def site_root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"

