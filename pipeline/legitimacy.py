from __future__ import annotations

import datetime as dt
import re

from pipeline.normalize import NormalizedJob
from pipeline.sources.base import RawJob

# Phrases that show up disproportionately often in scam/low-quality postings.
SCAM_PATTERNS = [
    re.compile(r"\bno experience necessary\b", re.I),
    re.compile(r"\bno interview\b", re.I),
    re.compile(r"\bwork from home.{0,20}(easy money|get rich)\b", re.I),
    re.compile(r"\bcrypto\b.{0,20}\binvestment\b", re.I),
    re.compile(r"\bwire transfer\b", re.I),
    re.compile(r"\bpay(ment)? upfront\b", re.I),
    re.compile(r"\btelegram\b", re.I),
    re.compile(r"\bwhatsapp\b.{0,20}\bonly\b", re.I),
    re.compile(r"\bgmail\.com\b"),  # legit companies rarely list a personal gmail as contact
]

MAX_AGE_DAYS = 45


def score(raw: RawJob, nj: NormalizedJob) -> int:
    """Return a 0-100 legitimacy score. Higher = more trustworthy."""
    points = 0

    # Source trust tier is the dominant signal.
    tier_points = {1: 55, 2: 35, 3: 15}
    points += tier_points.get(raw.source_trust_tier, 20)

    # Company/domain match: ATS-sourced jobs get this for free via company_id.
    if raw.source_trust_tier == 1 and nj.company_id is not None:
        points += 15

    # Has a real description of reasonable length (thin postings are a mild red flag).
    if nj.description and len(nj.description) > 200:
        points += 10
    elif not nj.description:
        points -= 10

    # Recency.
    if nj.posted_at:
        age_days = (dt.datetime.now(dt.timezone.utc) - _as_aware(nj.posted_at)).days
        if age_days > MAX_AGE_DAYS:
            points -= 20
        elif age_days <= 7:
            points += 10
    else:
        points -= 5  # no posted date at all is a minor red flag

    # Scam-pattern scan across title + description.
    haystack = f"{nj.title} {nj.description or ''}"
    hits = sum(1 for pattern in SCAM_PATTERNS if pattern.search(haystack))
    points -= hits * 20

    # Apply URL sanity check: must be a real-looking https URL.
    if not nj.apply_url.startswith("https://"):
        points -= 15

    return max(0, min(100, points))


def _as_aware(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value
