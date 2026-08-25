"""
Extract stage.

Pulls current + hourly weather data for each configured location from the
Open-Meteo API (no API key required), with retry/backoff on failure, and
writes the raw JSON responses to data/raw/ before any transformation
happens. Keeping the untouched raw response on disk means a bad transform
can always be re-run against the original data.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

from src.utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> Dict[str, Any]:
    with open(PROJECT_ROOT / "config" / "config.yaml", "r") as f:
        return yaml.safe_load(f)


def fetch_weather_for_location(
    location: Dict[str, Any], api_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fetch weather data for a single location, retrying on failure.

    Raises the last exception if all retries are exhausted, so the caller
    (main.py) can decide whether to fail the whole run or continue with
    partial data.
    """
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "UTC",
    }

    last_error = None
    for attempt in range(1, api_config["max_retries"] + 1):
        try:
            logger.info(
                f"Fetching weather for {location['name']} "
                f"(attempt {attempt}/{api_config['max_retries']})"
            )
            response = requests.get(
                api_config["base_url"],
                params=params,
                timeout=api_config["timeout_seconds"],
            )
            response.raise_for_status()
            data = response.json()
            data["_location_name"] = location["name"]
            data["_fetched_at"] = datetime.now(timezone.utc).isoformat()
            return data

        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning(f"Fetch failed for {location['name']}: {exc}")
            if attempt < api_config["max_retries"]:
                sleep_for = api_config["retry_backoff_seconds"] * attempt
                logger.info(f"Retrying in {sleep_for}s...")
                time.sleep(sleep_for)

    logger.error(
        f"All {api_config['max_retries']} attempts failed for {location['name']}"
    )
    raise last_error


def extract_all(config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Fetch weather for every configured location.

    Individual location failures are logged and skipped rather than
    crashing the whole run — a transient issue with one city shouldn't
    block the other N-1 from loading.
    """
    config = config or load_config()
    api_config = config["api"]
    locations = config["locations"]

    results = []
    for location in locations:
        try:
            data = fetch_weather_for_location(location, api_config)
            results.append(data)
        except Exception:
            logger.error(f"Skipping {location['name']} after repeated failures.")
            continue

    logger.info(f"Extracted data for {len(results)}/{len(locations)} locations.")
    return results


def save_raw(records: List[Dict[str, Any]], config: Dict[str, Any] = None) -> Path:
    """Persist the raw API responses to data/raw/ as timestamped JSON."""
    config = config or load_config()
    raw_dir = PROJECT_ROOT / config["pipeline"]["raw_data_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = raw_dir / f"weather_raw_{timestamp}.json"

    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)

    logger.info(f"Saved raw data to {out_path}")
    return out_path


if __name__ == "__main__":
    cfg = load_config()
    raw_records = extract_all(cfg)
    save_raw(raw_records, cfg)
