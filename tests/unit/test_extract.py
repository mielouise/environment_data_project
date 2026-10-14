"""Unit tests for extraction layer."""

from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.extract import DMIDataSource
from app.extract.dmi import build_dmi_collection_url


@patch("app.extract.dmi.requests.get")
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


@patch("app.extract.dmi.requests.get")
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


@patch("app.extract.dmi.requests.get")
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


@patch("app.extract.dmi.requests.get")
def test_dmi_data_source_fetch_passes_query_and_follows_pages(mock_get):
    first_response = MagicMock()
    first_response.json.return_value = {
        "features": [{"id": "first"}],
        "links": [
            {
                "href": "http://fake-url.com?parameterId=temp_dry&offset=1",
                "rel": "next",
            }
        ],
    }
    second_response = MagicMock()
    second_response.json.return_value = {
        "features": [{"id": "second"}],
        "links": [],
    }
    mock_get.side_effect = [first_response, second_response]
    source = DMIDataSource("DMI", "DMI API", "http://fake-url.com")

    result = source.fetch(params={"parameterId": "temp_dry", "limit": 1})

    assert result["features"] == [{"id": "first"}, {"id": "second"}]
    assert mock_get.call_args_list[0].kwargs == {
        "timeout": 10,
        "params": {"parameterId": "temp_dry", "limit": 1},
    }
    assert mock_get.call_args_list[1].args == (
        "http://fake-url.com?parameterId=temp_dry&offset=1",
    )


@pytest.mark.parametrize(
    ("base_url", "collection", "expected_url"),
    [
        (
            "https://opendataapi.dmi.dk",
            "observation",
            "https://opendataapi.dmi.dk/v2/metObs/collections/"
            "observation/items",
        ),
        (
            "https://opendataapi.dmi.dk/v2/metObs/collections",
            "observation",
            "https://opendataapi.dmi.dk/v2/metObs/collections/"
            "observation/items",
        ),
        (
            "https://opendataapi.dmi.dk/v2/metObs/collections",
            "station",
            "https://opendataapi.dmi.dk/v2/metObs/collections/station/items",
        ),
        (
            "http://localhost:8080/",
            "station",
            "http://localhost:8080/v2/metObs/collections/station/items",
        ),
        (
            "https://opendataapi.dmi.dk/v2/metObs/collections/"
            "observation/items",
            "station",
            "https://opendataapi.dmi.dk/v2/metObs/collections/station/items",
        ),
        (
            "http://localhost:8080/proxy/v2/metObs/collections",
            "observation",
            "http://localhost:8080/proxy/v2/metObs/collections/"
            "observation/items",
        ),
    ],
)
def test_build_dmi_collection_url(base_url, collection, expected_url):
    assert build_dmi_collection_url(base_url, collection) == expected_url


def test_build_dmi_collection_url_rejects_unknown_collection():
    with pytest.raises(ValueError, match="Unsupported DMI collection"):
        build_dmi_collection_url("https://opendataapi.dmi.dk", "unknown")


@pytest.mark.parametrize(
    "base_url",
    [
        "opendataapi.dmi.dk",
        "ftp://opendataapi.dmi.dk",
        "https://opendataapi.dmi.dk?token=secret",
        "https://opendataapi.dmi.dk#fragment",
    ],
)
def test_build_dmi_collection_url_rejects_invalid_base_url(base_url):
    with pytest.raises(ValueError, match="DMI API base URL"):
        build_dmi_collection_url(base_url, "observation")