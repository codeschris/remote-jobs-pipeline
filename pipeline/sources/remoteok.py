from __future__ import annotations

import datetime as dt

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.sources.base import RawJob

URL = "https://remoteok.com/api"

DEV_KEYWORDS = (
    "dev", "engineer", "engineering", "software", "backend", "frontend",
    "full stack", "fullstack", "swe", "programmer", "sre", "devops", "data engineer",
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch(client: httpx.Client) -> list[dict]:
    resp = client.get(URL, headers={"User-Agent": "remote-jobs-pipeline/1.0"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # First element is usually a legal/metadata blob, not a job
    return [d for d in data if isinstance(d, dict) and d.get("id")]


class RemoteOKSource:
    name = "remoteok"

    def fetch(self) -> list[RawJob]:
        with httpx.Client() as client:
            try:
                raw_jobs = _fetch(client)
            except httpx.HTTPError:
                return []

        jobs: list[RawJob] = []
        for j in raw_jobs:
            title = j.get("position") or j.get("title") or ""
            if not _looks_like_dev_job(title, j.get("tags") or []):
                continue

            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(j["id"]),
                    title=title,
                    apply_url=j.get("url") or f"https://remoteok.com/l/{j['id']}",
                    company_name=j.get("company"),
                    description=j.get("description"),
                    location=j.get("location") or "Remote",
                    tags=j.get("tags") or [],
                    posted_at=_parse_epoch(j.get("epoch")),
                    remote=True,
                    source_trust_tier=2,
                )
            )
        return jobs


def _looks_like_dev_job(title: str, tags: list[str]) -> bool:
    haystack = f"{title} {' '.join(tags)}".lower()
    return any(kw in haystack for kw in DEV_KEYWORDS)


def _parse_epoch(value) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)
    except (ValueError, TypeError):
        return None
