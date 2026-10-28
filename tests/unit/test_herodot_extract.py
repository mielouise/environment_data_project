"""Unit tests for the Herodot extraction source."""

from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.extract import HerodotDataSource


def _source() -> HerodotDataSource:
    return HerodotDataSource(
        source_id="HERODOT",
        source_name="Herodot Sensor API",
        api_token="test-token",
    )


def test_herodot_source_reads_token_and_url_from_environment(monkeypatch):
    monkeypatch.setenv("SENSOR_API_TOKEN", "test-token")
    monkeypatch.setenv("SENSOR_API_URL", "https://example.test/observations")

    source = HerodotDataSource.from_environment()

    assert source.api_token == "test-token"
    assert source.url == "https://example.test/observations"


def test_herodot_source_requires_environment_token(monkeypatch):
    monkeypatch.delenv("SENSOR_API_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="SENSOR_API_TOKEN"):
        HerodotDataSource.from_environment()


@patch("app.extract.herodot.requests.get")
def test_herodot_fetch_sends_bearer_token_and_returns_json(mock_get):
    response = MagicMock()
    response.json.return_value = {"items": [{"sensor": "temperature"}]}
    mock_get.return_value = response

    result = _source().fetch()

    assert result == {"items": [{"sensor": "temperature"}]}
    mock_get.assert_called_once_with(
        "https://herodot.spac.dk/api/v1/observations",
        headers={"Authorization": "Bearer test-token"},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


@patch("app.extract.herodot.requests.get")
def test_herodot_fetch_passes_query_parameters(mock_get):
    response = MagicMock()
    response.json.return_value = {"items": []}
    mock_get.return_value = response

    _source().fetch(params={"limit": 10, "sensor": "temperature"})

    assert mock_get.call_args.kwargs["params"] == {
        "limit": 10,
        "sensor": "temperature",
    }


@patch("app.extract.herodot.requests.get")
def test_herodot_fetch_wraps_request_failures(mock_get):
    request_error = RequestException("Request failed")
    mock_get.side_effect = request_error

    with pytest.raises(RuntimeError, match="Failed to retrieve Herodot data") as exc:
        _source().fetch()

    assert exc.value.__cause__ is request_error


@patch("app.extract.herodot.requests.get")
def test_herodot_fetch_rejects_non_object_json(mock_get):
    response = MagicMock()
    response.json.return_value = [{"sensor": "temperature"}]
    mock_get.return_value = response

    with pytest.raises(RuntimeError, match="must be a JSON object"):
        _source().fetch()


@pytest.mark.parametrize(
    ("api_token",),
    [("",)],
)
def test_herodot_source_requires_token(api_token):
    with pytest.raises(ValueError, match="API token"):
        HerodotDataSource(
            source_id="HERODOT",
            source_name="Herodot Sensor API",
            api_token=api_token,
        )
