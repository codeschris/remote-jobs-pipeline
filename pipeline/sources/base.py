from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawJob:
    """Unified shape every source adapter must produce, before normalization/scoring."""

    source: str                       # 'greenhouse' | 'lever' | 'remoteok' | 'arbeitnow' | 'remotive'
    external_id: str                  # unique within `source`
    title: str
    apply_url: str
    company_name: str | None = None
    company_slug: str | None = None   # set when it's a known ATS company from companies.yaml
    description: str | None = None
    location: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: dt.datetime | None = None
    remote: bool | None = None        # explicit remote flag from the source, if it provides one
    source_trust_tier: int = 2        # 1 = ATS/company-direct, 2 = reputable aggregator API, 3 = scraped


class Source(Protocol):
    name: str

    def fetch(self) -> list[RawJob]:
        """Fetch and return all currently-listed jobs from this source."""
        ...
