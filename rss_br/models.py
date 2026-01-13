from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Literal


FeedKind = Literal["rss", "atom", "xml", "unknown"]


@dataclass(slots=True)
class FeedRecord:
    url: str
    kind: FeedKind = "unknown"
    title: str | None = None
    homepage: str | None = None
    language: str | None = None
    entries: int | None = None
    topics: list[str] = field(default_factory=list)
    fetched_at: str | None = None
    status_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "FeedRecord":
        return FeedRecord(
            url=d.get("url", ""),
            kind=d.get("kind", "unknown"),
            title=d.get("title"),
            homepage=d.get("homepage"),
            language=d.get("language"),
            entries=d.get("entries"),
            topics=list(d.get("topics") or []),
            fetched_at=d.get("fetched_at"),
            status_code=d.get("status_code"),
            error=d.get("error"),
        )


@dataclass(slots=True)
class SiteRecord:
    name: str
    site_url: str
    source: str
    feeds: list[FeedRecord] = field(default_factory=list)
    discovered_candidates: list[str] = field(default_factory=list)
    fetched_at: str | None = None
    status_code: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["feeds"] = [f.to_dict() for f in self.feeds]
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "SiteRecord":
        feeds = [FeedRecord.from_dict(x) for x in (d.get("feeds") or [])]
        return SiteRecord(
            name=d.get("name", ""),
            site_url=d.get("site_url", ""),
            source=d.get("source", ""),
            feeds=feeds,
            discovered_candidates=list(d.get("discovered_candidates") or []),
            fetched_at=d.get("fetched_at"),
            status_code=d.get("status_code"),
            error=d.get("error"),
        )


@dataclass(slots=True)
class ScanMeta:
    started_at: str
    finished_at: str | None = None
    source: str = "wikidata"
    max_sites: int | None = None
    max_workers: int = 20
    timeout_s: float = 15.0

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ScanMeta":
        return ScanMeta(
            started_at=d.get("started_at", ""),
            finished_at=d.get("finished_at"),
            source=d.get("source", "wikidata"),
            max_sites=d.get("max_sites"),
            max_workers=int(d.get("max_workers", 20)),
            timeout_s=float(d.get("timeout_s", 15.0)),
        )


@dataclass(slots=True)
class ScanResult:
    meta: ScanMeta
    sites: list[SiteRecord]

    def to_dict(self) -> dict[str, Any]:
        return {"meta": self.meta.to_dict(), "sites": [s.to_dict() for s in self.sites]}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ScanResult":
        meta = ScanMeta.from_dict(d.get("meta") or {})
        sites = [SiteRecord.from_dict(x) for x in (d.get("sites") or [])]
        return ScanResult(meta=meta, sites=sites)

