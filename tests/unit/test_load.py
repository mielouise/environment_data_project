"""Repository tests."""
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.load import MeasurementRepository
from app.transform import MeasurementDTO
from app.transform_stations import StationDTO


def test_save_source():
    conn = MagicMock()
    repo = MeasurementRepository(conn)
    repo.save_source("DMI", "DMI", "API_DMI")
    assert "dim_sources" in conn.cursor.return_value.__enter__.return_value.execute.call_args.args[0]
    conn.commit.assert_called_once()


def test_save_measurement_includes_station():
    conn = MagicMock()
    repo = MeasurementRepository(conn)
    record = MeasurementDTO("DMI", 1, datetime(2026, 1, 1, tzinfo=timezone.utc), 2.5, "06030")
    repo.save_measurements([record])
    query, rows = conn.cursor.return_value.__enter__.return_value.executemany.call_args.args
    assert "station_id" in query
    assert rows[0][-1] == "06030"


def test_save_stations():
    conn = MagicMock()
    repo = MeasurementRepository(conn)
    repo.save_stations([StationDTO("06030", "Station", 55.7, 12.4)])
    assert conn.cursor.return_value.__enter__.return_value.executemany.called


def test_empty_records_do_not_write():
    conn = MagicMock()
    repo = MeasurementRepository(conn)
    repo.save_measurements([])
    repo.save_stations([])
    conn.cursor.assert_not_called()
