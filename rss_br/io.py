from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from rss_br.models import ScanResult


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_scan_json(path: Path, result: ScanResult) -> None:
    write_json(path, result.to_dict())


def write_scan_csv(path: Path, result: ScanResult) -> None:
    """
    CSV "achatado": 1 linha por feed.
    """
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "site_name",
                "site_url",
                "source",
                "site_error",
                "feed_url",
                "feed_kind",
                "feed_title",
                "feed_homepage",
                "feed_language",
                "feed_entries",
                "feed_topics",
                "feed_error",
            ],
        )
        w.writeheader()
        for s in result.sites:
            if s.feeds:
                for feed in s.feeds:
                    w.writerow(
                        {
                            "site_name": s.name,
                            "site_url": s.site_url,
                            "source": s.source,
                            "site_error": s.error or "",
                            "feed_url": feed.url,
                            "feed_kind": feed.kind,
                            "feed_title": feed.title or "",
                            "feed_homepage": feed.homepage or "",
                            "feed_language": feed.language or "",
                            "feed_entries": feed.entries if feed.entries is not None else "",
                            "feed_topics": " | ".join(feed.topics),
                            "feed_error": feed.error or "",
                        }
                    )
            else:
                # linha vazia para sites sem feed válido
                w.writerow(
                    {
                        "site_name": s.name,
                        "site_url": s.site_url,
                        "source": s.source,
                        "site_error": s.error or "",
                        "feed_url": "",
                        "feed_kind": "",
                        "feed_title": "",
                        "feed_homepage": "",
                        "feed_language": "",
                        "feed_entries": "",
                        "feed_topics": "",
                        "feed_error": "",
                    }
                )

