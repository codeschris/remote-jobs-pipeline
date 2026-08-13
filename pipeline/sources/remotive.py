from __future__ import annotations

import datetime as dt

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.sources.base import RawJob

URL = "https://remotive.com/api/remote-jobs"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch(client: httpx.Client) -> list[dict]:
    resp = client.get(URL, params={"category": "software-dev"}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


class RemotiveSource:
    name = "remotive"

    def fetch(self) -> list[RawJob]:
        with httpx.Client() as client:
            try:
                raw_jobs = _fetch(client)
            except httpx.HTTPError:
                return []

        jobs: list[RawJob] = []
        for j in raw_jobs:
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(j["id"]),
                    title=j.get("title", ""),
                    apply_url=j.get("url", ""),
                    company_name=j.get("company_name"),
                    description=j.get("description"),
                    location=j.get("candidate_required_location") or "Remote",
                    tags=j.get("tags") or [],
                    posted_at=_parse_dt(j.get("publication_date")),
                    remote=True,
                    source_trust_tier=2,
                )
            )
        return jobs


def _parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
