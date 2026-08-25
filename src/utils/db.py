"""
Database connection helpers.

Uses SQLAlchemy so the same code works against Postgres in production
and SQLite locally (handy for CI and for anyone cloning the repo who
doesn't want to spin up Postgres just to try the pipeline).

Connection info comes from environment variables (.env), never hardcoded.
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.utils.logger import get_logger

logger = get_logger(__name__)

load_dotenv()


def get_database_url() -> str:
    """
    Build the DB connection URL from env vars.

    Falls back to a local SQLite file if Postgres env vars aren't set,
    so `python src/main.py` works out of the box with zero setup.
    """
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    pg_host = os.getenv("POSTGRES_HOST")
    if pg_host:
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_password = os.getenv("POSTGRES_PASSWORD", "")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "weather_etl")
        return f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    logger.warning(
        "No POSTGRES_HOST or DATABASE_URL found in environment. "
        "Falling back to local SQLite at data/weather_etl.db. "
        "Set these in .env to use Postgres."
    )
    return "sqlite:///data/weather_etl.db"


_engine = None
_SessionLocal = None


def get_engine(echo: bool = False):
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(url, echo=echo, future=True)
        logger.debug(f"Created DB engine for: {url.split('@')[-1]}")
    return _engine


def get_session_factory(echo: bool = False):
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(echo=echo), future=True)
    return _SessionLocal


@contextmanager
def get_session(echo: bool = False):
    """Context manager that commits on success and rolls back on error."""
    session_factory = get_session_factory(echo=echo)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("DB session rolled back due to an error.")
        raise
    finally:
        session.close()
