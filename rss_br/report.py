from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from rss_br.models import ScanResult


def topic_summary(result: ScanResult, *, min_count: int = 1) -> dict[str, Any]:
    """
    Gera um resumo por tópico/categoria baseado nos feeds encontrados.
    """
    topic_to_sites: dict[str, set[str]] = defaultdict(set)
    topic_to_feeds: Counter[str] = Counter()

    for site in result.sites:
        for feed in site.feeds:
            if feed.error:
                continue
            for t in feed.topics:
                key = " ".join(t.split())
                if not key:
                    continue
                topic_to_sites[key].add(site.site_url)
                topic_to_feeds[key] += 1

    rows = []
    for topic, feeds_count in topic_to_feeds.most_common():
        if feeds_count < min_count:
            continue
        rows.append(
            {
                "topic": topic,
                "feeds": feeds_count,
                "sites": len(topic_to_sites[topic]),
            }
        )

    return {
        "topics": rows,
        "total_topics": len(rows),
    }

