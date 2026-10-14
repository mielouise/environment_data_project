"""Unit tests for extraction layer."""

from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.extract import DMIDataSource


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
@patch('app.extract.dmi.requests.get')
def test_pagination_preserves_filters_and_collects_all_pages(mock_get):
    first, second = MagicMock(), MagicMock()
    first.json.return_value = {'features': [{'id': 1}], 'links': [
        {'rel': 'next', 'href': '?parameterId=temp_dry&offset=1'}]}
    second.json.return_value = {'features': [{'id': 2}]}
    mock_get.side_effect = [first, second]
    source = DMIDataSource('DMI', 'DMI', 'https://example.test/items')
    assert source.fetch({'parameterId': 'temp_dry'}) == {'features': [{'id': 1}, {'id': 2}]}
    assert mock_get.call_args_list[0].kwargs['params'] == {'parameterId': 'temp_dry'}
    assert 'params' not in mock_get.call_args_list[1].kwargs

@patch('app.extract.dmi.requests.get')
@pytest.mark.parametrize('href', ['https://evil.test/items', 'https://example.test/other', 'https://example.test/items'])
def test_unsafe_or_repeating_next_page_rejected(mock_get, href):
    mock_get.return_value.json.return_value = {'features': [], 'links': [{'rel': 'next', 'href': href}]}
    source = DMIDataSource('DMI', 'DMI', 'https://example.test/items')
    with pytest.raises(RuntimeError):
        source.fetch()

@patch('app.extract.dmi.requests.get')
def test_station_endpoint_receives_only_station_filters(mock_get):
    mock_get.return_value.json.return_value = {'features': []}
    source = DMIDataSource('DMI', 'DMI', 'https://example.test/v2/metObs/collections/observation/items?api-key=test&parameterId=temp_dry')
    source.fetch_stations({'stationId': '06101'})
    mock_get.assert_called_once_with('https://example.test/v2/metObs/collections/station/items',
                                    params={'api-key': 'test', 'stationId': '06101'}, timeout=10)
