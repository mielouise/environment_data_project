"""Unit tests for the repository layer."""

from datetime import (
    UTC,
    datetime,
)
from unittest.mock import MagicMock

from app.load import MeasurementRepository
from app.transform import MeasurementDTO, StationDTO


def test_save_source():
    """Verify source metadata is persisted."""

    mock_conn = MagicMock()

    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    repository = MeasurementRepository(db_connection=mock_conn)

    repository.save_source("SOURCE-01", "Sensor Name", "API_DMI")

    mock_cursor.execute.assert_called_once()
    query, parameters = mock_cursor.execute.call_args.args
    assert "INSERT INTO dim_sources" in query
    assert "ON CONFLICT (source_id)" in query
    assert parameters == (
        "SOURCE-01",
        "Sensor Name",
        "API_DMI",
    )

    mock_conn.commit.assert_not_called()


def test_save_measurements_success():
    """Verify source-less DMI measurements use the legacy conflict key."""

    mock_conn = MagicMock()

    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    repository = MeasurementRepository(db_connection=mock_conn)

    measurement = MeasurementDTO(
        source_id="DMI",
        station_id="05329",
        parameter_id=1,
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        value=15.0,
    )

    repository.save_measurements([measurement])

    mock_cursor.executemany.assert_called_once()
    query, rows = mock_cursor.executemany.call_args.args
    assert "INSERT INTO fact_measurements" in query
    assert "ON CONFLICT" in query
    assert "DO UPDATE SET" in query
    assert "WHERE source_reading_id IS NULL AND source_id <> 'HERODOT'" in query
    assert rows == [
        (
            "DMI",
            "05329",
            1,
            datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
            15.0,
            None,
            None,
        )
    ]

    mock_conn.commit.assert_not_called()


def test_save_measurements_preserves_distinct_source_readings():
    """Use source IDs to retain readings that share station and timestamp."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    repository = MeasurementRepository(mock_conn)
    timestamp = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    records = [
        MeasurementDTO(
            source_id="HERODOT",
            station_id="node-123",
            parameter_id=1,
            timestamp=timestamp,
            value=value,
            source_observation_id=f"observation-{reading_id}",
            source_reading_id=reading_id,
        )
        for reading_id, value in (("reading-1", 15.0), ("reading-2", 16.0))
    ]

    repository.save_measurements(records)

    query, rows = mock_cursor.executemany.call_args.args
    assert "ON CONFLICT (source_id, source_reading_id)" in query
    assert len(rows) == 2
    assert [row[-1] for row in rows] == ["reading-1", "reading-2"]


def test_save_measurements_inserts_unidentified_herodot_rows_without_upsert():
    """Avoid collapsing Herodot rows when the source provides no reading ID."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    repository = MeasurementRepository(mock_conn)
    measurement = MeasurementDTO(
        source_id="HERODOT",
        station_id="node-123",
        parameter_id=1,
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        value=15.0,
    )

    repository.save_measurements([measurement])

    query, rows = mock_cursor.executemany.call_args.args
    assert "ON CONFLICT" not in query
    assert rows[0][-2:] == (None, None)


def test_save_measurements_empty():
    """Verify empty collections skip database work."""

    mock_conn = MagicMock()

    repository = MeasurementRepository(db_connection=mock_conn)

    repository.save_measurements([])

    mock_conn.cursor.assert_not_called()


def test_save_stations_upserts_latest_station_location():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    repository = MeasurementRepository(mock_conn)
    station = StationDTO(
        station_id="05329",
        name="Outrup",
        station_type="Pluvio",
        country_code="DNK",
        latitude=55.723,
        longitude=8.3327,
        station_height=18.0,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )

    repository.save_stations([station])

    query, rows = mock_cursor.executemany.call_args.args
    assert "INSERT INTO dim_stations" in query
    assert "station_name" in query
    assert "ON CONFLICT (station_id)" in query
    assert "COALESCE" in query
    assert rows == [
        (
            "05329",
            "Outrup",
            "Pluvio",
            "DNK",
            55.723,
            8.3327,
            18.0,
            datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    mock_conn.commit.assert_not_called()


def test_save_stations_supports_unknown_herodot_metadata():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    repository = MeasurementRepository(mock_conn)
    node = StationDTO(
        station_id="node-123",
        name=None,
        station_type="sensor_node",
        country_code=None,
        latitude=None,
        longitude=None,
        station_height=None,
        valid_from=None,
    )

    repository.save_stations([node])

    _, rows = mock_cursor.executemany.call_args.args
    assert rows == [("node-123", None, "sensor_node", None, None, None, None, None)]


def test_save_stations_empty_skips_database_work():
    mock_conn = MagicMock()

    MeasurementRepository(mock_conn).save_stations([])

    mock_conn.cursor.assert_not_called()
