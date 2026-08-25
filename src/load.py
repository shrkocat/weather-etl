"""
Load stage.

Writes the validated DataFrame into the database using an upsert (insert,
or update on conflict) keyed on (location_name, observation_time), so
re-running the pipeline for the same day is idempotent instead of
creating duplicate rows.
"""

from typing import Any, Dict

import pandas as pd
from sqlalchemy import Table, MetaData, inspect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.utils.db import get_engine, get_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_schema(engine, table_name: str):
    """Confirm the target table exists; fail fast with a clear message if not."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        raise RuntimeError(
            f"Table '{table_name}' does not exist. "
            f"Run `psql -f sql/schema.sql` (or scripts/setup_db.sh) first."
        )


def load(df: pd.DataFrame, config: Dict[str, Any]) -> int:
    """
    Upsert rows into the database. Returns the number of rows written.
    """
    if df.empty:
        logger.warning("Nothing to load — DataFrame is empty.")
        return 0

    table_name = config["database"]["table_name"]
    engine = get_engine(echo=config["database"].get("echo_sql", False))
    ensure_schema(engine, table_name)

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    records = df.to_dict(orient="records")
    dialect = engine.dialect.name

    with get_session() as session:
        for record in records:
            if dialect == "postgresql":
                stmt = pg_insert(table).values(**record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["location_name", "observation_time"],
                    set_={k: v for k, v in record.items()
                          if k not in ("location_name", "observation_time")},
                )
            else:
                # SQLite fallback (local dev / CI) — same upsert semantics
                stmt = sqlite_insert(table).values(**record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["location_name", "observation_time"],
                    set_={k: v for k, v in record.items()
                          if k not in ("location_name", "observation_time")},
                )
            session.execute(stmt)

    logger.info(f"Loaded {len(records)} row(s) into '{table_name}'.")
    return len(records)
