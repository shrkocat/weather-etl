import pandas as pd

from src.transform import transform, flatten_record


SAMPLE_RECORD = {
    "_location_name": "Manila",
    "_fetched_at": "2026-08-25T00:00:00+00:00",
    "latitude": 14.6,
    "longitude": 120.98,
    "current": {
        "time": "2026-08-25T00:00",
        "temperature_2m": 29.4,
        "relative_humidity_2m": 78,
        "wind_speed_10m": 12.3,
        "precipitation": 0.0,
    },
}


def test_flatten_record_produces_single_row():
    df = flatten_record(SAMPLE_RECORD)
    assert len(df) == 1
    assert df.iloc[0]["location_name"] == "Manila"
    assert df.iloc[0]["temperature_celsius"] == 29.4


def test_transform_returns_typed_dataframe():
    df = transform([SAMPLE_RECORD])
    assert len(df) == 1
    assert pd.api.types.is_datetime64_any_dtype(df["observation_time"])
    assert pd.api.types.is_float_dtype(df["temperature_celsius"])


def test_transform_drops_duplicates():
    df = transform([SAMPLE_RECORD, SAMPLE_RECORD])
    assert len(df) == 1  # same location + observation_time -> deduped


def test_transform_drops_rows_missing_location():
    bad_record = dict(SAMPLE_RECORD)
    bad_record["_location_name"] = None
    df = transform([bad_record])
    assert df.empty


def test_transform_empty_input_returns_empty_dataframe_with_columns():
    df = transform([])
    assert df.empty
    assert "location_name" in df.columns


def test_transform_handles_missing_current_block_gracefully():
    record = {"_location_name": "Nowhere", "_fetched_at": "2026-08-25T00:00:00+00:00"}
    df = transform([record])
    # Missing observation_time -> row gets dropped as invalid, not a crash
    assert df.empty
