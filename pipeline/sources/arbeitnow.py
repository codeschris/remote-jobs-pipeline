from __future__ import annotations

import datetime as dt

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.sources.base import RawJob

URL = "https://www.arbeitnow.com/api/job-board-api"

DEV_KEYWORDS = (
    "dev", "engineer", "engineering", "software", "backend", "frontend",
    "full stack", "fullstack", "swe", "programmer", "sre", "devops",
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_page(client: httpx.Client, url: str) -> dict:
    resp = client.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


class ArbeitnowSource:
    name = "arbeitnow"

    def fetch(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        url = URL
        with httpx.Client() as client:
            # Paginate a few pages; arbeitnow returns a `links.next` field
            for _ in range(5):
                try:
                    payload = _fetch_page(client, url)
                except httpx.HTTPError:
                    break

                for j in payload.get("data", []):
                    if not j.get("remote"):
                        continue
                    title = j.get("title", "")
                    tags = j.get("tags") or []
                    if not _looks_like_dev_job(title, tags):
                        continue

                    jobs.append(
                        RawJob(
                            source=self.name,
                            external_id=str(j.get("slug") or j.get("url")),
                            title=title,
                            apply_url=j.get("url", ""),
                            company_name=j.get("company_name"),
                            description=j.get("description"),
                            location=j.get("location") or "Remote",
                            tags=tags,
                            posted_at=_parse_epoch(j.get("created_at")),
                            remote=True,
                            source_trust_tier=2,
                        )
                    )

                next_url = (payload.get("links") or {}).get("next")
                if not next_url:
                    break
                url = next_url
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
