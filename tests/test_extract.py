from unittest.mock import patch, MagicMock

import pytest
import requests

from src.extract import fetch_weather_for_location

API_CONFIG = {
    "base_url": "https://api.open-meteo.com/v1/forecast",
    "timeout_seconds": 5,
    "max_retries": 3,
    "retry_backoff_seconds": 0,  # no real waiting in tests
}

LOCATION = {"name": "Manila", "latitude": 14.6, "longitude": 120.98}


@patch("src.extract.requests.get")
def test_fetch_success_on_first_try(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"current": {"temperature_2m": 29.0}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = fetch_weather_for_location(LOCATION, API_CONFIG)

    assert result["_location_name"] == "Manila"
    assert "_fetched_at" in result
    assert mock_get.call_count == 1


@patch("src.extract.time.sleep", return_value=None)
@patch("src.extract.requests.get")
def test_fetch_retries_then_succeeds(mock_get, mock_sleep):
    fail_response = requests.RequestException("boom")
    success_response = MagicMock()
    success_response.json.return_value = {"current": {"temperature_2m": 29.0}}
    success_response.raise_for_status.return_value = None

    mock_get.side_effect = [fail_response, success_response]
    # First call raises via side_effect being an exception instance
    mock_get.side_effect = [requests.RequestException("boom"), success_response]

    result = fetch_weather_for_location(LOCATION, API_CONFIG)
    assert result["_location_name"] == "Manila"
    assert mock_get.call_count == 2


@patch("src.extract.time.sleep", return_value=None)
@patch("src.extract.requests.get")
def test_fetch_raises_after_exhausting_retries(mock_get, mock_sleep):
    mock_get.side_effect = requests.RequestException("network down")

    with pytest.raises(requests.RequestException):
        fetch_weather_for_location(LOCATION, API_CONFIG)

    assert mock_get.call_count == API_CONFIG["max_retries"]
