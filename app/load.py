"""Unit tests for the repository layer."""

from datetime import (
    datetime,
    timezone,
)
from unittest.mock import MagicMock

from load import MeasurementRepository
from transform import MeasurementDTO


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