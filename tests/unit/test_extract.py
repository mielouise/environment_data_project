"""Unit tests for extraction layer."""

from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.extract import DMIDataSource


@patch("app.extract.requests.get")
def test_dmi_data_source_fetch_success(
    mock_get
):
    """Verify successful API calls return JSON."""

    mock_response = MagicMock()

    mock_response.json.return_value = {
        "features": [
            {
                "properties": {
                    "value": 21.5
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None

    mock_get.return_value = mock_response

    source = DMIDataSource(
        source_id="TEST-01",
        source_name="Test Station",
        url="http://fake-url.com"
    )

    result = source.fetch()

    assert result == {
        "features": [
            {
                "properties": {
                    "value": 21.5
                }
            }
        ]
    }

    mock_response.raise_for_status.assert_called_once_with()
    mock_get.assert_called_once_with(
        "http://fake-url.com",
        timeout=10
    )


@patch("app.extract.requests.get")
def test_dmi_data_source_fetch_failure(
    mock_get
):
    """Verify API failures raise RuntimeError."""

    underlying_error = RequestException(
        "Network broken"
    )

    mock_get.side_effect = underlying_error

    source = DMIDataSource(
        source_id="TEST-01",
        source_name="Test Station",
        url="http://fake-url.com"
    )

    with pytest.raises(RuntimeError) as exc_info:
        source.fetch()

    assert (
        "Failed to retrieve DMI data"
        in str(exc_info.value)
    )

    assert (
        exc_info.value.__cause__
        == underlying_error
    )


@patch("app.extract.requests.get")
def test_dmi_data_source_fetch_http_failure(
    mock_get
):
    """Verify unsuccessful HTTP responses are raised as RuntimeError."""

    underlying_error = RequestException("HTTP request failed")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = underlying_error
    mock_get.return_value = mock_response

    source = DMIDataSource(
        source_id="TEST-01",
        source_name="Test Station",
        url="http://fake-url.com"
    )

    with pytest.raises(
        RuntimeError,
        match="Failed to retrieve DMI data"
    ) as exc_info:
        source.fetch()

    assert exc_info.value.__cause__ is underlying_error
    mock_response.json.assert_not_called()