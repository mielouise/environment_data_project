"""Unit tests for the database loading repository."""

from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.transform import MeasurementDTO
from app.load import MeasurementRepository


def test_measurement_repository_save_source():
    """Verifies that save_source executes the proper SQL dimension command."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    repo = MeasurementRepository(db_connection=mock_conn)
    repo.save_source("SOURCE-01", "Sensor Name", "HARDWARE_SENSOR")

    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_measurement_repository_save_measurements_success():
    """Verifies that the repository converts DTO maps into raw bulk execute calls."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    repo = MeasurementRepository(db_connection=mock_conn)
    test_dto = MeasurementDTO(
        source_id="DMI-01",
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
        temperature=15.0,
        humidity=75.0
    )

    repo.save_measurements([test_dto])

    mock_cursor.executemany.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_measurement_repository_save_measurements_empty():
    """Verifies that save_measurements exits early when given an empty collection."""
    mock_conn = MagicMock()
    repo = MeasurementRepository(db_connection=mock_conn)
    
    repo.save_measurements([])
    mock_conn.cursor.assert_not_called()
