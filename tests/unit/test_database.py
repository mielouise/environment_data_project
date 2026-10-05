"""Unit tests for the database management module."""

import pytest
from unittest.mock import patch, MagicMock
from app.database import create_tables, get_connection


@patch("app.database.psycopg.connect")
def test_get_connection_success(mock_connect):
    """Tests that get_connection successfully returns a live connection object."""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    conn = get_connection()
    assert conn == mock_conn
    mock_connect.assert_called_once()


@patch("app.database.psycopg.connect")
def test_get_connection_failure(mock_connect):
    """Tests that get_connection raises an exception when the driver crashes."""
    mock_connect.side_effect = Exception("Connection refused")

    with pytest.raises(Exception) as exc_info:
        get_connection()

    assert "Connection refused" in str(exc_info.value)


@patch("app.database.get_connection")
def test_create_tables_success(mock_get_connection):
    """Tests that create_tables executes the required DDL commands and commits."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    create_tables()

    # Verificer at cursor.execute blev kaldt for at oprette tabellerne
    assert mock_cursor.execute.call_count >= 2
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
