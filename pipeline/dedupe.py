from __future__ import annotations

from pipeline.normalize import NormalizedJob


def dedupe_cross_source(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """
    When the same posting appears via multiple sources (e.g. an aggregator
    re-lists a job that's also on the company's Greenhouse board), keep the
    one with the highest legitimacy score (ties broken by source_trust order
    already baked into the score).
    """
    best_by_hash: dict[str, NormalizedJob] = {}
    for job in jobs:
        current = best_by_hash.get(job.content_hash)
        if current is None or job.legitimacy_score > current.legitimacy_score:
            best_by_hash[job.content_hash] = job
    return list(best_by_hash.values())
