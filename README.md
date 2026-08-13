# remote-jobs-pipeline

Daily pipeline that pulls remote software dev/eng jobs from ATS feeds
(Greenhouse, Lever) and job board APIs (RemoteOK, Arbeitnow, Remotive),
normalizes them, scores legitimacy, and upserts into Postgres.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL (Neon)
```

## Run locally

```bash
python -m pipeline.main
```

First run will `CREATE TABLE IF NOT EXISTS` for `companies` and `jobs`
(see `pipeline/db.py::init_db`). No Alembic yet — add it once the schema
stabilizes.

## GitHub Actions

Add `DATABASE_URL` as a repo secret (Settings → Secrets and variables →
Actions). The workflow in `.github/workflows/daily.yml` runs
`python -m pipeline.main` every day at 06:00 UTC, or on demand via
"Run workflow".

## Project layout

```
pipeline/
  sources/
    base.py         # RawJob dataclass + Source protocol
    greenhouse.py    # ATS adapter (trust tier 1)
    lever.py         # ATS adapter (trust tier 1)
    remoteok.py      # API adapter (trust tier 2)
    arbeitnow.py      # API adapter (trust tier 2)
    remotive.py      # API adapter (trust tier 2)
  normalize.py        # RawJob -> NormalizedJob (seniority/tag inference, content hash)
  legitimacy.py        # 0-100 scoring heuristics
  dedupe.py            # cross-source dedupe by content hash
  models.py            # SQLAlchemy 2.0 models (Company, Job)
  db.py                # session factory, upsert, stale-job deactivation
  main.py              # orchestrator
companies.yaml           # ATS company list (add more slugs here)
```

## Adding a company (ATS source)

Open the company's careers page, check the network tab while it loads
job listings:
- **Greenhouse**: look for a call to `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- **Lever**: look for a call to `api.lever.co/v0/postings/{slug}`

Add an entry to `companies.yaml` with the matching `slug`.

## Alembic migrations

```bash
pip install -r requirements.txt   # includes alembic>=1.13
alembic upgrade head               # run on first deploy or after each new migration
alembic revision --autogenerate -m "describe change"  # generate a new migration
```

The initial migration (`alembic/versions/001_initial_schema.py`) creates the
`companies` and `jobs` tables. `pipeline/db.py::init_db` (which calls
`create_all`) is still present for local bootstrapping but Alembic is the
canonical migration path.

## Dashboard

```bash
cd dashboard
cp .env.example .env.local    # fill in DATABASE_URL (same Neon DB)
npm install
npm run dev                   # http://localhost:3000
```

Stack: Next.js 15 (App Router) + Drizzle ORM + `@neondatabase/serverless`.

Filters available: seniority, source, minimum legitimacy score, tag.

## CLI options

```bash
# Only store senior/staff/lead jobs
python -m pipeline.main --seniority senior,staff,lead

# Raise the legitimacy floor
python -m pipeline.main --min-score 50
```

## Not done yet (picking up from here)

- [x] Dashboard (Next.js + Drizzle, reading from the same Neon DB) — see `dashboard/`
- [x] Alembic migrations instead of `create_all` — see `alembic/`
- [x] Expand `companies.yaml` with more remote-first companies — 15 → 21 companies
- [ ] Tune `legitimacy.py` thresholds once you see real score distributions
- [x] `seniority` filter fed by CLI args (`--seniority`) and dashboard UI
- [x] Rate-limit / backoff tuning — 429-aware retry + inter-company sleep in Greenhouse/Lever adapters
