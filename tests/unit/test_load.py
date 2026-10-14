"""Unit tests for PostgreSQL loading with station history."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.load import MeasurementRepository
from app.transform import MeasurementDTO, StationDTO


def test_save_source():
    conn = MagicMock()
    MeasurementRepository(conn).save_source("DMI", "DMI", "API_DMI")
    assert "dim_sources" in conn.cursor.return_value.__enter__.return_value.execute.call_args.args[0]
    conn.commit.assert_called_once()


def test_save_measurement_includes_station():
    conn = MagicMock()
    record = MeasurementDTO(
        "DMI", 1, datetime(2026, 1, 1, tzinfo=timezone.utc), 2.5, "06030"
    )
    MeasurementRepository(conn).save_measurements([record])
    cursor = conn.cursor.return_value.__enter__.return_value
    queries = cursor.executemany.call_args_list
    assert len(queries) == 2  # Missing station placeholder, followed by measurement.
    sql, rows = queries[-1].args
    assert "station_id" in sql
    assert rows[0][-1] == "06030"
    assert cursor.execute.called  # Link measurement with valid station metadata.


def test_save_stations_keeps_all_versions():
    conn = MagicMock()
    stations = [
        StationDTO("06030", "Old", 55.0, 12.0,
                   valid_from=datetime(2019, 1, 1, tzinfo=timezone.utc),
                   valid_to=datetime(2022, 1, 1, tzinfo=timezone.utc)),
        StationDTO("06030", "New", 55.7, 12.4,
                   valid_from=datetime(2022, 1, 1, tzinfo=timezone.utc)),
    ]
    MeasurementRepository(conn).save_stations(stations)
    cursor = conn.cursor.return_value.__enter__.return_value
    calls = cursor.executemany.call_args_list
    assert len(calls) == 2
    assert len(calls[0].args[1]) == 1  # Latest station metadata.
    assert calls[0].args[1][0][1] == "New"
    assert len(calls[1].args[1]) == 2  # Both historical versions.


def test_empty_records_do_not_write():
    conn = MagicMock()
    repository = MeasurementRepository(conn)
    repository.save_measurements([])
    repository.save_stations([])
    conn.cursor.assert_not_called()
