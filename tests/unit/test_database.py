"""Unit tests for the database module."""

from unittest.mock import MagicMock, patch

import pytest

from app.database import create_tables, get_connection


@patch("app.database.psycopg.connect")
def test_get_connection_success(mock_connect):
    """Verify successful database connection creation."""

    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    connection = get_connection()

    assert connection == mock_conn
    mock_connect.assert_called_once()


@patch("app.database.psycopg.connect")
def test_get_connection_failure(mock_connect):
    """Verify connection errors are propagated."""

    mock_connect.side_effect = Exception(
        "Connection refused"
    )

    with pytest.raises(Exception) as exc_info:
        get_connection()

    assert "Connection refused" in str(
        exc_info.value
    )


@patch("app.database.get_connection")
def test_create_tables_success(
    mock_get_connection
):
    """Verify schema creation executes and commits."""

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    mock_get_connection.return_value = mock_conn

    create_tables()

    assert mock_cursor.execute.call_count >= 4

    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once