"""DMI extraction tests."""
from unittest.mock import Mock, patch
import pytest
import requests
from app.extract import DMIDataSource


def source():
    return DMIDataSource("DMI", "DMI", "https://example.test/items")


@patch("app.extract.dmi.requests.get")
def test_fetch_passes_filters(mock_get):
    mock_get.return_value.json.return_value = {"features": [{"id": "1"}]}
    result = source().fetch({"parameterId": "temp_dry", "limit": 10})
    assert len(result["features"]) == 1
    assert mock_get.call_args.kwargs["params"]["parameterId"] == "temp_dry"
    assert mock_get.call_args.kwargs["timeout"] == 10


@patch("app.extract.dmi.requests.get")
def test_fetch_paginates(mock_get):
    first = Mock()
    first.json.return_value = {"features": [{"id": "a"}, {"id": "b"}]}
    second = Mock()
    second.json.return_value = {"features": [{"id": "c"}]}
    mock_get.side_effect = [first, second]
    assert len(source().fetch({"limit": 2})["features"]) == 3
    assert mock_get.call_count == 2


@patch("app.extract.dmi.requests.get", side_effect=requests.RequestException("down"))
def test_fetch_network_failure(mock_get):
    with pytest.raises(RuntimeError, match="Failed to retrieve DMI data"):
        source().fetch()


@patch("app.extract.dmi.requests.get")
def test_fetch_rejects_invalid_payload(mock_get):
    mock_get.return_value.json.return_value = {"other": []}
    with pytest.raises(RuntimeError, match="Unexpected DMI"):
        source().fetch()
