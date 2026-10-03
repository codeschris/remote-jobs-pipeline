from __future__ import annotations

import datetime as dt
import os

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from pipeline.models import Base, Company, Job
from pipeline.normalize import NormalizedJob


def get_database_url() -> URL:
    url = make_url(os.environ["DATABASE_URL"])
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg2")
    return url


def get_engine():
    url = get_database_url()
    return create_engine(url, pool_pre_ping=True)


def get_session_factory(engine=None) -> sessionmaker[Session]:
    engine = engine or get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine=None) -> None:
    """Create tables if they don't exist.

    This is kept for local dev convenience and first-run bootstrapping.
    In production (or any environment with an existing schema), prefer running
    Alembic migrations instead:

        alembic upgrade head
    """
    engine = engine or get_engine()
    Base.metadata.create_all(engine)


def get_or_create_company(session: Session, name: str, slug: str, ats: str | None, domain: str | None) -> Company:
    company = session.scalar(select(Company).where(Company.slug == slug))
    if company is None:
        company = Company(name=name, slug=slug, ats_provider=ats, domain=domain)
        session.add(company)
        session.flush()
    return company


def upsert_job(session: Session, nj: NormalizedJob) -> Job:
    """Insert a job or update it if already seen (matched on source + external_id)."""
    existing = session.scalar(
        select(Job).where(Job.source == nj.source, Job.external_id == nj.external_id)
    )
    now = dt.datetime.now(dt.timezone.utc)

    if existing is None:
        job = Job(
            source=nj.source,
            external_id=nj.external_id,
            company_id=nj.company_id,
            title=nj.title,
            description=nj.description,
            apply_url=nj.apply_url,
            location=nj.location,
            seniority=nj.seniority,
            tags=nj.tags,
            legitimacy_score=nj.legitimacy_score,
            posted_at=nj.posted_at,
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
            content_hash=nj.content_hash,
        )
        session.add(job)
        return job

    existing.title = nj.title
    existing.description = nj.description
    existing.apply_url = nj.apply_url
    existing.location = nj.location
    existing.seniority = nj.seniority
    existing.tags = nj.tags
    existing.legitimacy_score = nj.legitimacy_score
    existing.content_hash = nj.content_hash
    existing.last_seen_at = now
    existing.is_active = True
    return existing


def deactivate_stale(session: Session, source: str, seen_external_ids: set[str]) -> int:
    """Mark jobs from `source` not present in this run's fetch as inactive."""
    stale_jobs = session.scalars(
        select(Job).where(Job.source == source, Job.is_active.is_(True))
    ).all()
    count = 0
    for job in stale_jobs:
        if job.external_id not in seen_external_ids:
            job.is_active = False
            count += 1
    return count
