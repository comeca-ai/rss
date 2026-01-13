from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SourceSite:
    name: str
    site_url: str
    source: str

