"""Unit tests for the repository layer."""

from datetime import (
    datetime,
    timezone,
)
from unittest.mock import MagicMock

from app.load import MeasurementRepository
from app.transform import MeasurementDTO, StationDTO


def test_save_source():
    """Verify source metadata is persisted."""

    mock_conn = MagicMock()

    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    repository = MeasurementRepository(
        db_connection=mock_conn
    )

    repository.save_source(
        "SOURCE-01",
        "Sensor Name",
        "API_DMI"
    )

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
    """Verify measurements are converted to bulk insert rows."""

    mock_conn = MagicMock()

    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    repository = MeasurementRepository(
        db_connection=mock_conn
    )

    measurement = MeasurementDTO(
        source_id="DMI",
        station_id="05329",
        parameter_id=1,
        timestamp=datetime(
            2026,
            10,
            5,
            12,
            0,
            tzinfo=timezone.utc
        ),
        value=15.0
    )

    repository.save_measurements(
        [measurement]
    )

    mock_cursor.executemany.assert_called_once()
    query, rows = mock_cursor.executemany.call_args.args
    assert "INSERT INTO fact_measurements" in query
    assert "ON CONFLICT" in query
    assert "DO UPDATE SET" in query
    assert rows == [
        (
            "DMI",
            "05329",
            1,
            datetime(
                2026,
                10,
                5,
                12,
                0,
                tzinfo=timezone.utc
            ),
            15.0,
        )
    ]

    mock_conn.commit.assert_not_called()


def test_save_measurements_empty():
    """Verify empty collections skip database work."""

    mock_conn = MagicMock()

    repository = MeasurementRepository(
        db_connection=mock_conn
    )

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
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    repository.save_stations([station])

    query, rows = mock_cursor.executemany.call_args.args
    assert "INSERT INTO dim_stations" in query
    assert "station_name" in query
    assert "ON CONFLICT (station_id)" in query
    assert "EXCLUDED.valid_from >= dim_stations.valid_from" in query
    assert rows == [
        (
            "05329",
            "Outrup",
            "Pluvio",
            "DNK",
            55.723,
            8.3327,
            18.0,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ]
    mock_conn.commit.assert_not_called()


def test_save_stations_empty_skips_database_work():
    mock_conn = MagicMock()

    MeasurementRepository(mock_conn).save_stations([])

    mock_conn.cursor.assert_not_called()
