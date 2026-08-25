# Weather ETL Pipeline

A daily ETL pipeline that fetches weather data for multiple cities from
the [Open-Meteo API](https://open-meteo.com/) (free, no API key
required), cleans and validates it with pandas, loads it into
PostgreSQL, and visualizes it in a Streamlit dashboard.

```
Open-Meteo API → Python (extract) → pandas (transform) → validate → PostgreSQL → Streamlit
```

Built to demonstrate patterns closer to real data engineering than a
typical ML side project: idempotent loads, data validation, structured
logging, retry/backoff on network calls, config/secrets separation,
CI, and containerization.

## Features

- **Extract**: pulls current weather for multiple cities, with retry +
  exponential backoff on API failures
- **Transform**: flattens nested JSON into a typed, deduplicated
  pandas DataFrame
- **Validate**: rejects empty/malformed data, flags out-of-range
  values, blocks duplicate rows before they hit the database
- **Load**: idempotent upsert into PostgreSQL (safe to re-run)
- **Dashboard**: Streamlit app for latest readings, trends, and
  summary stats
- **Tests**: unit tests for transform/validate/extract logic
- **Logging**: structured logs to console + rotating log file
- **CI**: GitHub Actions runs lint + tests against a real Postgres
  service container on every push
- **Docker**: one-command local stack (Postgres + pipeline + dashboard)

## Project structure

```
weather-etl-pipeline/
│
├── src/
│   ├── extract.py          # API → data/raw/*.json
│   ├── transform.py        # raw JSON → clean DataFrame
│   ├── validate.py         # sanity checks before load
│   ├── load.py             # DataFrame → Postgres (upsert)
│   ├── main.py             # orchestrates the full run
│   └── utils/
│       ├── logger.py       # centralized logging config
│       └── db.py           # SQLAlchemy engine/session helpers
│
├── config/
│   ├── config.yaml         # non-secret settings
│   └── logging.yaml        # logging format/handlers
│
├── data/
│   ├── raw/                # untouched API responses (gitignored)
│   └── processed/          # cleaned CSVs (gitignored)
│
├── sql/
│   ├── schema.sql          # current schema
│   └── migrations/         # versioned schema changes
│
├── dashboard/
│   └── app.py              # Streamlit dashboard
│
├── scripts/
│   ├── run_pipeline.sh
│   └── setup_db.sh
│
├── tests/
│   ├── test_extract.py
│   ├── test_transform.py
│   └── test_validation.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── .github/workflows/ci.yml
├── docs/architecture.md
├── notebooks/exploration.ipynb
├── logs/                   # rotating log file lands here
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting started

### Option A: Docker (recommended, zero local setup)

```bash
cp .env.example .env
cd docker
docker compose up --build
```

This starts Postgres, applies `sql/schema.sql`, runs the pipeline once,
and starts the dashboard at http://localhost:8501.

To re-run the pipeline manually against the running stack:

```bash
docker compose run app python -m src.main
```

### Option B: Local Python

Requires Python 3.10+ and a running Postgres instance (or use the
`postgres` service from `docker/docker-compose.yml` on its own).

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then fill in your DB credentials
./scripts/setup_db.sh             # creates the DB + applies schema.sql

python -m src.main                # run the pipeline once
streamlit run dashboard/app.py    # view the dashboard
```

Note: if no Postgres connection info is found in `.env`, the pipeline
falls back to a local SQLite file (`data/weather_etl.db`) so you can
try it with zero database setup. Set `POSTGRES_HOST` (or
`DATABASE_URL`) in `.env` to use real Postgres.

### Running on a schedule

For a genuinely daily pipeline, wire `scripts/run_pipeline.sh` into:
- a cron job (`0 6 * * * /path/to/scripts/run_pipeline.sh`), or
- a scheduled GitHub Actions workflow (`on: schedule:`), or
- Airflow/Prefect if you want retries, backfills, and a UI

## Running tests

```bash
pytest tests/ -v --cov=src
```

Dry-run the pipeline without writing to the database:

```bash
python -m src.main --dry-run
```

## Configuration

| What | Where |
|---|---|
| Cities to track, API URL, retry settings | `config/config.yaml` |
| Validation thresholds (temp/humidity ranges, null tolerance) | `config/config.yaml` |
| Logging format and destinations | `config/logging.yaml` |
| Database credentials, connection string | `.env` (never committed — see `.env.example`) |

See [`docs/architecture.md`](docs/architecture.md) for the reasoning
behind these design choices and ideas for extending the project.

## Tech demonstrated

Python · pandas · requests · SQL · PostgreSQL · SQLAlchemy · ETL/ELT
concepts · structured logging · retry/backoff · data validation ·
idempotent upserts · pytest · GitHub Actions CI · Docker Compose ·
Streamlit
