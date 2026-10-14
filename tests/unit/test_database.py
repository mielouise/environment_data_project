"""Unit tests for database connection utilities."""

from unittest.mock import patch

import pytest

from app.database import get_connection, get_db_connection


@patch("app.database.psycopg.connect")
def test_get_connection_success(mock_connect):
    mock_connect.return_value = object()

    assert get_connection() is mock_connect.return_value
    mock_connect.assert_called_once()


@patch("app.database.psycopg.connect")
def test_get_connection_failure(mock_connect):
    mock_connect.side_effect = Exception("Connection refused")

    with pytest.raises(Exception, match="Connection refused"):
        get_connection()


@patch("app.database.get_connection")
def test_get_db_connection_delegates_to_get_connection(mock_get_connection):
    mock_get_connection.return_value = object()

    assert get_db_connection() is mock_get_connection.return_value

    mock_get_connection.assert_called_once_with()
