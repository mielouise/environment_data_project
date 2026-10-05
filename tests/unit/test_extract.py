"""Unit tests for the extraction module."""

import pytest
from unittest.mock import patch, MagicMock
from requests import RequestException
from app.extract import DMIDataSource


@patch("app.extract.requests.get")
def test_dmi_data_source_fetch_success(mock_get):
    """Tests that fetch returns the correctly structured dictionary upon HTTP 200."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"features": [{"properties": {"value": 21.5}}]}
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    source = DMIDataSource(source_id="TEST-01", source_name="Test Station", url="http://fake-url.com")
    result = source.fetch()

    assert result == {"features": [{"properties": {"value": 21.5}}]}
    mock_get.assert_called_once_with("http://fake-url.com", timeout=10)


@patch("app.extract.requests.get")
def test_dmi_data_source_fetch_failure(mock_get):
    """Tests that a network exception is wrapped inside a custom RuntimeError with cause."""
    underlying_err = RequestException("Network broken")
    mock_get.side_effect = underlying_err
    source = DMIDataSource(source_id="TEST-01", source_name="Test Station", url="http://fake-url.com")

    with pytest.raises(RuntimeError) as exc_info:
        source.fetch()
        
    assert "Kunne ikke hente data fra DMI" in str(exc_info.value)
    # Verificerer 'from err' linjen i din kildekode ekspliciet:
    assert exc_info.value.__cause__ == underlying_err
