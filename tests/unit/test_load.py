"""Unit tests for the repository layer."""

from datetime import (
    datetime,
    timezone,
)
from unittest.mock import MagicMock

from app.load import MeasurementRepository
from app.transform import MeasurementDTO


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

    mock_conn.commit.assert_called_once()


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
            1,
            None,
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

    mock_conn.commit.assert_called_once()


def test_save_measurements_empty():
    """Verify empty collections skip database work."""

    mock_conn = MagicMock()

    repository = MeasurementRepository(
        db_connection=mock_conn
    )

    repository.save_measurements([])

    mock_conn.cursor.assert_not_called()


def test_close():
    """Verify repository closes connection."""

    mock_conn = MagicMock()

    repository = MeasurementRepository(
        db_connection=mock_conn
    )

    repository.close()

    mock_conn.close.assert_called_once()
def test_upsert_keeps_station_in_conflict_key():
    conn = MagicMock()
    repository = MeasurementRepository(conn)
    repository.save_measurements([MeasurementDTO('DMI', 1, datetime.now(timezone.utc), 10, '06101')])
    query, rows = conn.cursor.return_value.__enter__.return_value.executemany.call_args.args
    assert 'station_id' in query.split('ON CONFLICT')[1].split('DO UPDATE')[0]
    assert rows[0][2] == '06101'

def test_save_station_metadata():
    from app.models import StationDTO
    conn = MagicMock()
    MeasurementRepository(conn).save_stations([StationDTO('DMI', '06101', 'Station', 12, 55, {'status': 'Active'})])
    query, rows = conn.cursor.return_value.__enter__.return_value.executemany.call_args.args
    assert 'ON CONFLICT (source_id, station_id)' in query
    assert rows[0][:5] == ('DMI', '06101', 'Station', 12, 55)
    conn.commit.assert_called_once()
