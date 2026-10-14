"""Unit tests for the DMI pipeline."""

from datetime import UTC, datetime
from threading import Barrier, current_thread
from unittest.mock import MagicMock

import pytest

from app.pipeline import run_dmi_pipeline
from app.transform import MeasurementDTO, StationDTO


def test_pipeline_extracts_transforms_and_persists_measurements(monkeypatch):
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    observation_source.fetch.return_value = {"features": []}
    station_source = MagicMock()
    station_source.fetch.return_value = {"features": []}
    repository = MagicMock()
    connection = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )

    assert (
        run_dmi_pipeline(
            observation_source,
            station_source,
            ("temp_dry", "humidity"),
        )
        == 0
    )

    station_source.fetch.assert_called_once_with(
        params={
            "bbox": "7,54,16,58",
            "limit": 1000,
        }
    )
    assert observation_source.fetch.call_count == 2
    assert {
        call.kwargs["params"]["parameterId"]
        for call in observation_source.fetch.call_args_list
    } == {"temp_dry", "humidity"}
    assert all(
        call.kwargs["params"]["bbox"] == "7,54,16,58"
        and call.kwargs["params"]["sortorder"] == "observed,DESC"
        and call.kwargs["params"]["limit"] == 1000
        and "/" in call.kwargs["params"]["datetime"]
        for call in observation_source.fetch.call_args_list
    )
    repository.save_source.assert_called_once_with(
        source_id="DMI",
        source_name="DMI Observation API",
        source_type="API_DMI",
    )
    repository.save_stations.assert_called_once_with([])
    repository.save_measurements.assert_called_once_with([])
    connection.transaction.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_pipeline_logs_counts_and_reasons_for_skipped_records(
    monkeypatch,
    caplog,
):
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    observation_source.fetch.return_value = {
        "features": [
            {
                "properties": {
                    "stationId": "05329",
                    "parameterId": "unknown",
                    "observed": "2026-10-14T10:00:00Z",
                    "value": 1,
                }
            }
        ]
    }
    station_source = MagicMock()
    station_source.fetch.return_value = {"features": []}
    connection = MagicMock()
    repository = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )

    assert (
        run_dmi_pipeline(
            observation_source,
            station_source,
            ("temp_dry",),
        )
        == 0
    )

    assert "DMI observations unexpected skips:" in caplog.text
    assert "'unsupported_parameter': 1" in caplog.text
    assert "WARNING" in caplog.text
    repository.save_measurements.assert_called_once_with([])


def test_pipeline_logs_replaced_station_versions_as_info(
    monkeypatch,
    caplog,
):
    caplog.set_level("INFO")
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    observation_source.fetch.return_value = {"features": []}
    station_source = MagicMock()
    station_source.fetch.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [8.3, 55.7]},
                "properties": {
                    "stationId": "05329",
                    "name": "Outrup",
                    "type": "Pluvio",
                    "country": "DNK",
                    "validFrom": "2020-01-01T00:00:00Z",
                },
            },
            {
                "geometry": {"coordinates": [8.4, 55.8]},
                "properties": {
                    "stationId": "05329",
                    "name": "Outrup",
                    "type": "Pluvio",
                    "country": "DNK",
                    "validFrom": "2026-01-01T00:00:00Z",
                },
            },
        ]
    }
    connection = MagicMock()
    repository = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )

    run_dmi_pipeline(
        observation_source,
        station_source,
        ("temp_dry",),
    )

    deduplication_log = next(
        record
        for record in caplog.records
        if "DMI stations expected skips:" in record.getMessage()
    )
    assert deduplication_log.levelname == "INFO"
    assert "'superseded_station_version': 1" in deduplication_log.message
    assert not any(
        record.levelname == "WARNING" and "DMI stations" in record.getMessage()
        for record in caplog.records
    )
    repository.save_stations.assert_called_once()
    assert len(repository.save_stations.call_args.args[0]) == 1


def test_pipeline_fetches_parameters_concurrently(monkeypatch):
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    station_source = MagicMock()
    station_source.fetch.return_value = {"features": []}
    connection = MagicMock()
    repository = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )
    simultaneous_requests = Barrier(2)
    worker_threads = set()

    def fetch_observations(*, params):
        worker_threads.add(current_thread().name)
        simultaneous_requests.wait(timeout=2)
        return {"features": []}

    observation_source.fetch.side_effect = fetch_observations

    run_dmi_pipeline(
        observation_source,
        station_source,
        ("temp_dry", "humidity"),
    )

    assert len(worker_threads) == 2


def test_pipeline_propagates_station_fetch_errors_before_opening_database(
    monkeypatch,
):
    observation_source = MagicMock()
    station_source = MagicMock()
    station_source.fetch.side_effect = RuntimeError("DMI server is down")
    get_connection = MagicMock()
    monkeypatch.setattr("app.pipeline.get_db_connection", get_connection)

    with pytest.raises(RuntimeError, match="DMI server is down"):
        run_dmi_pipeline(
            observation_source,
            station_source,
            ("temp_dry",),
        )

    observation_source.fetch.assert_not_called()
    get_connection.assert_not_called()


def test_pipeline_rejects_empty_parameter_selection():
    observation_source = MagicMock()
    station_source = MagicMock()
    with pytest.raises(ValueError, match="At least one DMI parameter"):
        run_dmi_pipeline(
            observation_source,
            station_source,
            (),
        )

    station_source.fetch.assert_not_called()
    observation_source.fetch.assert_not_called()


def test_pipeline_links_observations_to_persisted_station_metadata(
    monkeypatch,
):
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    observation_source.fetch.return_value = {
        "features": [
            {
                "properties": {
                    "stationId": "05329",
                    "parameterId": "temp_dry",
                    "observed": "2026-10-14T10:00:00Z",
                    "value": 12.5,
                }
            }
        ]
    }
    station_source = MagicMock()
    station_source.fetch.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [8.3327, 55.723]},
                "properties": {
                    "stationId": "05329",
                    "name": "Outrup",
                    "type": "Pluvio",
                    "country": "DNK",
                    "stationHeight": 18.0,
                    "validFrom": "2026-01-01T00:00:00Z",
                },
            }
        ]
    }
    repository = MagicMock()
    connection = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )

    assert (
        run_dmi_pipeline(
            observation_source,
            station_source,
            ("temp_dry",),
        )
        == 1
    )

    repository.save_stations.assert_called_once()
    assert repository.save_stations.call_args.args[0][0] == StationDTO(
        station_id="05329",
        name="Outrup",
        station_type="Pluvio",
        country_code="DNK",
        latitude=55.723,
        longitude=8.3327,
        station_height=18.0,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    repository.save_measurements.assert_called_once()
    assert repository.save_measurements.call_args.args[0] == [
        MeasurementDTO(
            source_id="DMI",
            station_id="05329",
            parameter_id=1,
            timestamp=datetime(2026, 10, 14, 10, 0, tzinfo=UTC),
            value=12.5,
        )
    ]


def test_pipeline_rolls_back_and_closes_connection_when_loading_fails(
    monkeypatch,
):
    observation_source = MagicMock()
    observation_source.source_id = "DMI"
    observation_source.source_name = "DMI Observation API"
    observation_source.fetch.return_value = {"features": []}
    station_source = MagicMock()
    station_source.fetch.return_value = {"features": []}
    repository = MagicMock()
    repository.save_measurements.side_effect = RuntimeError("Database error")
    connection = MagicMock()
    monkeypatch.setattr(
        "app.pipeline.get_db_connection",
        MagicMock(return_value=connection),
    )
    monkeypatch.setattr(
        "app.pipeline.MeasurementRepository",
        MagicMock(return_value=repository),
    )

    with pytest.raises(RuntimeError, match="Database error"):
        run_dmi_pipeline(
            observation_source,
            station_source,
            ("temp_dry",),
        )

    connection.transaction.return_value.__exit__.assert_called_once()
    assert (
        connection.transaction.return_value.__exit__.call_args.args[0] is RuntimeError
    )
    connection.close.assert_called_once_with()
