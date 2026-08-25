# Architecture

## Overview

```
Open-Meteo API
      │
      ▼
  extract.py  ──► data/raw/*.json        (untouched API responses)
      │
      ▼
  transform.py ──► data/processed/*.csv  (cleaned, typed, deduped)
      │
      ▼
  validate.py  ──► pass/fail + warnings
      │
      ▼
  load.py      ──► PostgreSQL (upsert)
      │
      ▼
  dashboard/app.py (Streamlit, reads from Postgres)
```

`src/main.py` orchestrates all four stages and is what a scheduler
(cron, GitHub Actions on a schedule, Airflow, etc.) calls once a day.

## Why these design choices

**Raw data is persisted before transformation.**
If a transform bug ships, we can re-run it against the exact API
response that was originally fetched, instead of losing that day's
data or hitting the API again (which may return different data by
then, since it's a forecast API).

**Upsert instead of insert.**
The pipeline is meant to run daily and be safely re-runnable. Loading
uses `(location_name, observation_time)` as a natural key and upserts
on conflict, so re-running the same day's job twice doesn't create
duplicate rows.

**SQLAlchemy instead of raw psycopg2.**
Lets the same code path run against SQLite locally/in CI (zero setup)
and Postgres in production, without maintaining two versions of
`load.py`.

**Validation is a separate stage from transformation.**
Transform's job is to produce a clean shape. Validate's job is to
decide whether that data is trustworthy enough to load. Keeping them
separate means validation rules (acceptable temperature ranges, null
thresholds) can change without touching cleaning logic, and the
pipeline can fail loudly on bad data instead of loading garbage.

**Config vs. secrets.**
`config/config.yaml` holds anything safe to commit (API URL,
locations, validation thresholds). `.env` holds anything that
shouldn't be public (DB password). This split is why `.gitignore`
excludes `.env` but not `config/`.

## Extending this project

Ideas for going further, roughly in order of effort:

1. Add more weather metrics (UV index, air quality) — just extend the
   `current` params in `extract.py` and the corresponding schema column.
2. Swap Open-Meteo for a provider that needs an API key, to demonstrate
   key-based auth handling via `.env`.
3. Add a `dbt` layer on top of the raw Postgres table for downstream
   modeling (staging → marts).
4. Replace the daily cron/GitHub Actions schedule with Airflow or
   Prefect for retries, backfills, and a UI.
5. Add a `data/raw` → data lake (S3/GCS) step before Postgres, to
   demonstrate a two-tier ELT pattern (land raw, transform in
   warehouse) instead of an ETL pattern.
