"""Tests for the new station-aware observation and migration behavior."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.load import MeasurementRepository
from app.transform import transform_observation


def test_station_id_is_retained_in_measurement():
    observation = {"properties": {
        "stationId": "06181", "parameterId": "temp_dry",
        "observed": "2026-01-01T12:00:00Z", "value": 10.5,
    }}
    result = transform_observation(observation, "DMI")
    assert result.station_id == "06181"
    assert result.timestamp == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_invalid_infinite_value_is_discarded():
    observation = {"properties": {
        "stationId": "06181", "parameterId": "temp_dry",
        "observed": "2026-01-01T12:00:00Z", "value": float("inf"),
    }}
    assert transform_observation(observation, "DMI") is None


def test_repository_upserts_unknown_station_before_measurement():
    conn = MagicMock()
    repo = MeasurementRepository(conn)
    from app.transform import MeasurementDTO
    record = MeasurementDTO(
        "DMI", 1, datetime(2026, 1, 1, tzinfo=timezone.utc), 9.1, "06181"
    )
    repo.save_measurements([record])
    cursor = conn.cursor.return_value.__enter__.return_value
    assert cursor.executemany.call_count == 2
    first_query = cursor.executemany.call_args_list[0].args[0]
    assert "INSERT INTO dim_stations" in first_query
    second_query = cursor.executemany.call_args_list[1].args[0]
    assert "INSERT INTO fact_measurements" in second_query
