"""Unit tests for multi-stage orchestration."""
from unittest.mock import Mock
from app.pipelines.weather_pipeline import run_weather_pipeline


def test_pipeline_saves_stations_before_measurements():
    calls = []
    source = Mock(source_id="DMI", source_name="DMI")
    source.fetch.return_value = {"features": []}
    station_source = Mock()
    station_source.fetch.return_value = {"features": [{"properties": {"stationId": "123"}}]}
    repository = Mock()
    repository.save_stations.side_effect = lambda _: calls.append("stations")
    repository.save_measurements.side_effect = lambda _: calls.append("measurements")
    assert run_weather_pipeline(source, repository, station_source=station_source) == 0
    assert calls == ["stations", "measurements"]


def test_pipeline_fetches_multiple_parameters():
    source = Mock(source_id="DMI", source_name="DMI")
    source.fetch.return_value = {"features": []}
    repository = Mock()
    assert run_weather_pipeline(
        source, repository, params={"parameterIds": ["temp_dry", "humidity"], "limit": 25}
    ) == 0
    assert source.fetch.call_count == 2
    first, second = source.fetch.call_args_list
    assert first.kwargs["params"]["parameterId"] == "temp_dry"
    assert second.kwargs["params"]["parameterId"] == "humidity"
