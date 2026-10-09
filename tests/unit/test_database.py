"""Unit tests for the database module."""

from unittest.mock import MagicMock, patch

import pytest

from app.database import (
    create_tables,
    get_connection,
    get_db_connection,
)


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
def test_get_db_connection_delegates_to_get_connection(
    mock_get_connection
):
    """Verify the public connection helper delegates to get_connection."""

    mock_conn = MagicMock()
    mock_get_connection.return_value = mock_conn

    assert get_db_connection() is mock_conn

    mock_get_connection.assert_called_once_with()


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

    assert mock_cursor.execute.call_count == 7
    executed_sql = [
        call.args[0]
        for call in mock_cursor.execute.call_args_list
    ]
    expected_statements = (
        "CREATE TABLE IF NOT EXISTS dim_sources",
        "CREATE TABLE IF NOT EXISTS dim_parameters",
        "CREATE TABLE IF NOT EXISTS fact_measurements",
        "CREATE INDEX IF NOT EXISTS idx_fact_measurements_timestamp",
        "CREATE INDEX IF NOT EXISTS idx_fact_measurements_source",
        "CREATE INDEX IF NOT EXISTS idx_fact_measurements_parameter",
    )
    for statement in expected_statements:
        assert any(statement in sql for sql in executed_sql)

    assert "INSERT INTO dim_parameters" in executed_sql[-1]
    assert "ON CONFLICT (parameter_id)" in executed_sql[-1]

    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()
    mock_conn.close.assert_called_once()


@patch("app.database.get_connection")
def test_create_tables_rolls_back_and_closes_on_failure(
    mock_get_connection
):
    """Verify schema failures roll back and still close the connection."""

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = RuntimeError("Schema failure")
    mock_get_connection.return_value = mock_conn

    with pytest.raises(RuntimeError, match="Schema failure"):
        create_tables()

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once