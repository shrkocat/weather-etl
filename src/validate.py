"""
Validate stage.

Runs sanity checks on the cleaned DataFrame before it's allowed into the
database. This is what separates an ETL pipeline from a script that just
moves data around: bad data gets caught here instead of silently
corrupting the database or a downstream dashboard.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def raise_if_invalid(self):
        if not self.is_valid:
            raise ValueError(f"Validation failed: {'; '.join(self.errors)}")


def validate(df: pd.DataFrame, config: Dict[str, Any]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    rules = config["validation"]

    # 1. Structural check: required columns present
    required_cols = {
        "location_name",
        "observation_time",
        "temperature_celsius",
        "humidity_pct",
    }
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # 2. Empty dataset check
    if df.empty:
        errors.append("DataFrame is empty; nothing to load.")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    # 3. Null-rate check
    null_pct = df[list(required_cols)].isnull().mean().max()
    if null_pct > rules["max_allowed_null_pct"]:
        errors.append(
            f"Null rate {null_pct:.2%} exceeds allowed "
            f"{rules['max_allowed_null_pct']:.2%} in required columns."
        )

    # 4. Range checks (out-of-range values become warnings + get flagged,
    #    not silently dropped, so they're visible in logs and reports)
    temp_out_of_range = df[
        (df["temperature_celsius"] < rules["temperature_min_celsius"])
        | (df["temperature_celsius"] > rules["temperature_max_celsius"])
    ]
    if not temp_out_of_range.empty:
        warnings.append(
            f"{len(temp_out_of_range)} row(s) have temperature outside "
            f"[{rules['temperature_min_celsius']}, {rules['temperature_max_celsius']}]°C"
        )

    humidity_out_of_range = df[
        (df["humidity_pct"] < rules["humidity_min_pct"])
        | (df["humidity_pct"] > rules["humidity_max_pct"])
    ]
    if not humidity_out_of_range.empty:
        warnings.append(
            f"{len(humidity_out_of_range)} row(s) have humidity outside "
            f"[{rules['humidity_min_pct']}, {rules['humidity_max_pct']}]%"
        )

    # 5. Duplicate check (should already be handled in transform, but a
    #    validation stage should never just trust the previous stage)
    dupes = df.duplicated(subset=["location_name", "observation_time"]).sum()
    if dupes > 0:
        errors.append(f"{dupes} duplicate (location, observation_time) row(s) found.")

    is_valid = len(errors) == 0

    for w in warnings:
        logger.warning(w)
    if is_valid:
        logger.info("Validation passed.")
    else:
        logger.error(f"Validation failed: {errors}")

    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
