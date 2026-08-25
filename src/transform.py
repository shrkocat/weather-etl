"""
Transform stage.

Converts the raw, nested JSON from the API into a flat, typed pandas
DataFrame that's ready to load into the database:
  - one row per (location, observation timestamp)
  - consistent column names/types
  - duplicates and obviously-bad rows removed
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def flatten_record(record: Dict[str, Any]) -> pd.DataFrame:
    """
    Flatten one location's raw API response into rows.

    Open-Meteo returns a "current" reading plus an "hourly" forecast
    array; we keep the current reading as a single-row snapshot, which is
    what a daily scheduled job typically wants to store.
    """
    location_name = record.get("_location_name", "unknown")
    fetched_at = record.get("_fetched_at")
    current = record.get("current", {})

    row = {
        "location_name": location_name,
        "observation_time": current.get("time"),
        "temperature_celsius": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "precipitation_mm": current.get("precipitation"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "fetched_at": fetched_at,
    }
    return pd.DataFrame([row])


def transform(raw_records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Flatten, type-cast, and de-duplicate all raw records into one DataFrame."""
    if not raw_records:
        logger.warning("No raw records to transform; returning empty DataFrame.")
        return _empty_dataframe()

    frames = [flatten_record(r) for r in raw_records]
    df = pd.concat(frames, ignore_index=True)

    df["observation_time"] = pd.to_datetime(df["observation_time"], utc=True, errors="coerce")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True, errors="coerce")

    numeric_cols = [
        "temperature_celsius",
        "humidity_pct",
        "wind_speed_kmh",
        "precipitation_mm",
        "latitude",
        "longitude",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["location_name", "observation_time"])
    df = df.drop_duplicates(subset=["location_name", "observation_time"])
    after = len(df)
    if before != after:
        logger.info(f"Dropped {before - after} row(s) during cleaning (nulls/duplicates).")

    df["location_name"] = df["location_name"].str.strip()

    logger.info(f"Transformed {len(df)} row(s).")
    return df.reset_index(drop=True)


def _empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "location_name",
            "observation_time",
            "temperature_celsius",
            "humidity_pct",
            "wind_speed_kmh",
            "precipitation_mm",
            "latitude",
            "longitude",
            "fetched_at",
        ]
    )


def save_processed(df: pd.DataFrame, config: Dict[str, Any]) -> Path:
    """Persist the cleaned DataFrame to data/processed/ as CSV (audit trail)."""
    from datetime import datetime, timezone

    processed_dir = PROJECT_ROOT / config["pipeline"]["processed_data_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = processed_dir / f"weather_processed_{timestamp}.csv"
    df.to_csv(out_path, index=False)

    logger.info(f"Saved processed data to {out_path}")
    return out_path
