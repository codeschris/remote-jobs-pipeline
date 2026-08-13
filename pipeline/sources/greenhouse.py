from __future__ import annotations

import datetime as dt
import logging
import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pipeline.sources.base import RawJob

log = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

# Seconds to wait between per-company requests to avoid hammering the API.
_INTER_COMPANY_SLEEP = 0.5


def _is_rate_limited(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception(_is_rate_limited),
    reraise=True,
)
def _fetch_for_company(client: httpx.Client, slug: str) -> list[dict]:
    resp = client.get(BASE_URL.format(slug=slug), params={"content": "true"}, timeout=20)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        log.warning("Greenhouse 429 for slug=%s (Retry-After: %s)", slug, retry_after)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, companies: list[dict]):
        # companies: list of dicts from companies.yaml filtered to ats == 'greenhouse'
        self.companies = companies

    def fetch(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        with httpx.Client() as client:
            for i, company in enumerate(self.companies):
                if i > 0:
                    time.sleep(_INTER_COMPANY_SLEEP)
                slug = company["slug"]
                try:
                    raw_jobs = _fetch_for_company(client, slug)
                except httpx.HTTPError as exc:
                    log.warning("Greenhouse fetch failed for slug=%s: %s", slug, exc)
                    continue

                for j in raw_jobs:
                    location = (j.get("location") or {}).get("name")
                    updated_at = j.get("updated_at")
                    posted_at = _parse_dt(updated_at)

                    jobs.append(
                        RawJob(
                            source=self.name,
                            external_id=str(j["id"]),
                            title=j.get("title", ""),
                            apply_url=j.get("absolute_url", ""),
                            company_name=company["name"],
                            company_slug=slug,
                            description=(j.get("content") or None),
                            location=location,
                            tags=[],
                            posted_at=posted_at,
                            remote="remote" in (location or "").lower(),
                            source_trust_tier=1,
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
