from __future__ import annotations

import argparse
import logging
from collections import defaultdict

import yaml
from dotenv import load_dotenv

from pipeline.db import (
    deactivate_stale,
    get_or_create_company,
    get_session_factory,
    init_db,
    upsert_job,
)
from pipeline.dedupe import dedupe_cross_source
from pipeline.legitimacy import score as score_legitimacy
from pipeline.normalize import normalize
from pipeline.sources import (
    ArbeitnowSource,
    GreenhouseSource,
    LeverSource,
    RemoteOKSource,
    RemotiveSource,
)
from pipeline.sources.base import RawJob

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")

MIN_LEGITIMACY_SCORE = 30  # jobs below this are stored but flagged, never silently dropped

VALID_SENIORITY_LEVELS = {"junior", "mid", "senior", "lead", "staff", "principal"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remote jobs pipeline")
    parser.add_argument(
        "--seniority",
        metavar="LEVEL[,LEVEL...]",
        help=(
            "Only store jobs matching these seniority levels "
            f"(comma-separated, choices: {', '.join(sorted(VALID_SENIORITY_LEVELS))}). "
            "Jobs with no detected seniority are always included."
        ),
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=MIN_LEGITIMACY_SCORE,
        metavar="N",
        help=f"Minimum legitimacy score to store (default: {MIN_LEGITIMACY_SCORE})",
    )
    return parser.parse_args()


def load_companies() -> list[dict]:
    with open("companies.yaml") as f:
        data = yaml.safe_load(f)
    return data.get("companies", [])


def build_sources() -> list:
    companies = load_companies()
    greenhouse_companies = [c for c in companies if c.get("ats") == "greenhouse"]
    lever_companies = [c for c in companies if c.get("ats") == "lever"]

    return [
        GreenhouseSource(greenhouse_companies),
        LeverSource(lever_companies),
        RemoteOKSource(),
        ArbeitnowSource(),
        RemotiveSource(),
    ]


def run() -> None:
    args = parse_args()

    seniority_filter: set[str] | None = None
    if args.seniority:
        seniority_filter = {s.strip().lower() for s in args.seniority.split(",")}
        invalid = seniority_filter - VALID_SENIORITY_LEVELS
        if invalid:
            log.warning("Unknown seniority levels ignored: %s", ", ".join(sorted(invalid)))
            seniority_filter -= invalid
        log.info("Seniority filter active: %s", ", ".join(sorted(seniority_filter)))

    min_score = args.min_score

    load_dotenv()
    init_db()
    session_factory = get_session_factory()

    sources = build_sources()
    all_raw: list[RawJob] = []

    for source in sources:
        log.info("Fetching from %s...", source.name)
        try:
            raw_jobs = source.fetch()
        except Exception:
            log.exception("Source %s failed entirely, skipping", source.name)
            continue
        log.info("  -> %d jobs", len(raw_jobs))
        all_raw.extend(raw_jobs)

    with session_factory() as session:
        # Resolve/create Company rows for ATS-sourced jobs up front.
        company_id_by_slug: dict[str, int] = {}
        for c in load_companies():
            company = get_or_create_company(
                session, name=c["name"], slug=c["slug"], ats=c.get("ats"), domain=c.get("domain")
            )
            company_id_by_slug[c["slug"]] = company.id
        session.commit()

        normalized = []
        for raw in all_raw:
            company_id = company_id_by_slug.get(raw.company_slug) if raw.company_slug else None
            nj = normalize(raw, company_id)
            nj.legitimacy_score = score_legitimacy(raw, nj)
            normalized.append(nj)

        deduped = dedupe_cross_source(normalized)
        log.info("Normalized %d jobs -> %d after cross-source dedupe", len(normalized), len(deduped))

        # Apply seniority filter: drop jobs whose detected seniority is not in the allowed set.
        # Jobs with seniority=None (undetected) are always kept.
        if seniority_filter:
            before = len(deduped)
            deduped = [j for j in deduped if j.seniority is None or j.seniority in seniority_filter]
            log.info("Seniority filter dropped %d jobs (%d remaining)", before - len(deduped), len(deduped))

        below_threshold = sum(1 for j in deduped if j.legitimacy_score < min_score)
        if below_threshold:
            log.warning(
                "%d jobs scored below legitimacy threshold (%d) — stored but flagged, not hidden",
                below_threshold, min_score,
            )

        seen_ids_by_source: dict[str, set[str]] = defaultdict(set)
        for nj in deduped:
            upsert_job(session, nj)
            seen_ids_by_source[nj.source].add(nj.external_id)

        session.commit()

        # Mark jobs that disappeared from each source's latest fetch as inactive.
        total_deactivated = 0
        for source_name, seen_ids in seen_ids_by_source.items():
            total_deactivated += deactivate_stale(session, source_name, seen_ids)
        session.commit()

        log.info("Deactivated %d stale jobs", total_deactivated)
        log.info("Pipeline run complete. %d active jobs upserted.", len(deduped))


if __name__ == "__main__":
    run()
