from __future__ import annotations

import datetime as dt
import logging
import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from pipeline.sources.base import RawJob

log = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings/{slug}"

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
    resp = client.get(BASE_URL.format(slug=slug), params={"mode": "json"}, timeout=20)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After")
        log.warning("Lever 429 for slug=%s (Retry-After: %s)", slug, retry_after)
    resp.raise_for_status()
    return resp.json()


class LeverSource:
    name = "lever"

    def __init__(self, companies: list[dict]):
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
                    log.warning("Lever fetch failed for slug=%s: %s", slug, exc)
                    continue

                for j in raw_jobs:
                    categories = j.get("categories") or {}
                    location = categories.get("location")
                    posted_at = _parse_epoch_ms(j.get("createdAt"))
                    commitment = categories.get("commitment") or ""
                    team = categories.get("team") or ""

                    jobs.append(
                        RawJob(
                            source=self.name,
                            external_id=str(j["id"]),
                            title=j.get("text", ""),
                            apply_url=j.get("hostedUrl", ""),
                            company_name=company["name"],
                            company_slug=slug,
                            description=(j.get("descriptionPlain") or j.get("description") or None),
                            location=location,
                            tags=[t for t in [team, commitment] if t],
                            posted_at=posted_at,
                            remote="remote" in (location or "").lower(),
                            source_trust_tier=1,
                        )
                    )
        return jobs


def _parse_epoch_ms(value) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.timezone.utc)
    except (ValueError, TypeError):
        return None
