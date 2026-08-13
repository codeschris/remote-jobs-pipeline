from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass

from pipeline.sources.base import RawJob

SENIORITY_PATTERNS = [
    ("staff", re.compile(r"\bstaff\b", re.I)),
    ("principal", re.compile(r"\bprincipal\b", re.I)),
    ("lead", re.compile(r"\blead\b", re.I)),
    ("senior", re.compile(r"\b(senior|sr\.?)\b", re.I)),
    ("junior", re.compile(r"\b(junior|jr\.?|entry.?level|new.?grad|graduate)\b", re.I)),
    ("mid", re.compile(r"\b(mid.?level|intermediate)\b", re.I)),
]

TAG_KEYWORDS = {
    "python": re.compile(r"\bpython\b", re.I),
    "typescript": re.compile(r"\btypescript\b", re.I),
    "javascript": re.compile(r"\bjavascript\b", re.I),
    "go": re.compile(r"\b(golang|go)\b", re.I),
    "react": re.compile(r"\breact\b", re.I),
    "django": re.compile(r"\bdjango\b", re.I),
    "fastapi": re.compile(r"\bfastapi\b", re.I),
    "postgres": re.compile(r"\bpostgres(ql)?\b", re.I),
    "aws": re.compile(r"\baws\b", re.I),
    "backend": re.compile(r"\bback.?end\b", re.I),
    "frontend": re.compile(r"\bfront.?end\b", re.I),
    "fullstack": re.compile(r"\bfull.?stack\b", re.I),
    "devops": re.compile(r"\bdevops\b", re.I),
}


@dataclass
class NormalizedJob:
    source: str
    external_id: str
    title: str
    apply_url: str
    company_id: int | None
    description: str | None
    location: str | None
    seniority: str | None
    tags: list[str]
    posted_at: dt.datetime | None
    legitimacy_score: int
    content_hash: str


def infer_seniority(title: str) -> str | None:
    for label, pattern in SENIORITY_PATTERNS:
        if pattern.search(title):
            return label
    return None


def infer_tags(title: str, description: str | None, existing_tags: list[str]) -> list[str]:
    text = f"{title} {description or ''}"
    found = {tag for tag, pattern in TAG_KEYWORDS.items() if pattern.search(text)}
    # keep original source tags too (lowercased, deduped)
    found.update(t.lower() for t in existing_tags if t)
    return sorted(found)


def content_hash(title: str, company_name: str | None, description: str | None) -> str:
    basis = f"{(company_name or '').strip().lower()}|{title.strip().lower()}|{(description or '')[:500]}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def normalize(raw: RawJob, company_id: int | None) -> NormalizedJob:
    seniority = infer_seniority(raw.title)
    tags = infer_tags(raw.title, raw.description, raw.tags)

    return NormalizedJob(
        source=raw.source,
        external_id=raw.external_id,
        title=raw.title.strip(),
        apply_url=raw.apply_url,
        company_id=company_id,
        description=raw.description,
        location=raw.location,
        seniority=seniority,
        tags=tags,
        posted_at=raw.posted_at,
        legitimacy_score=50,  # placeholder; legitimacy.py sets the real value
        content_hash=content_hash(raw.title, raw.company_name, raw.description),
    )
