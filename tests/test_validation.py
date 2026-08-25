import pandas as pd
import pytest

from src.validate import validate

CONFIG = {
    "validation": {
        "temperature_min_celsius": -90,
        "temperature_max_celsius": 60,
        "humidity_min_pct": 0,
        "humidity_max_pct": 100,
        "max_allowed_null_pct": 0.05,
    }
}


def make_df(**overrides):
    base = {
        "location_name": ["Manila", "London"],
        "observation_time": pd.to_datetime(
            ["2026-08-25T00:00:00Z", "2026-08-25T00:00:00Z"]
        ),
        "temperature_celsius": [29.4, 18.2],
        "humidity_pct": [78, 65],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_dataframe_passes():
    df = make_df()
    result = validate(df, CONFIG)
    assert result.is_valid
    assert result.errors == []


def test_missing_required_column_fails():
    df = make_df().drop(columns=["humidity_pct"])
    result = validate(df, CONFIG)
    assert not result.is_valid
    assert any("Missing required columns" in e for e in result.errors)


def test_empty_dataframe_fails():
    df = make_df().iloc[0:0]
    result = validate(df, CONFIG)
    assert not result.is_valid
    assert any("empty" in e.lower() for e in result.errors)


def test_out_of_range_temperature_produces_warning_not_error():
    df = make_df(temperature_celsius=[150.0, 18.2])  # impossible temp
    result = validate(df, CONFIG)
    assert result.is_valid  # warnings don't block load
    assert any("temperature" in w.lower() for w in result.warnings)


def test_duplicate_rows_fail_validation():
    df = make_df()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    result = validate(df, CONFIG)
    assert not result.is_valid
    assert any("duplicate" in e.lower() for e in result.errors)


def test_raise_if_invalid_raises():
    df = make_df().iloc[0:0]
    result = validate(df, CONFIG)
    with pytest.raises(ValueError):
        result.raise_if_invalid()
