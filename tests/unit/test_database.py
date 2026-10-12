"""Unit tests for the database module."""

from hashlib import sha256
from unittest.mock import MagicMock, call, patch

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


def test_create_tables_applies_and_records_pending_migration(
    monkeypatch,
    tmp_path,
):
    """Verify migrations are executed and tracked in one transaction."""
    migration_sql = "CREATE TABLE example (id INTEGER);"
    migration_path = tmp_path / "0001_create_example.sql"
    migration_path.write_text(migration_sql, encoding="utf-8")
    monkeypatch.setattr("app.database.MIGRATIONS_DIR", tmp_path)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    monkeypatch.setattr(
        "app.database.get_connection",
        MagicMock(return_value=mock_conn),
    )

    create_tables()

    executed_calls = mock_cursor.execute.call_args_list
    assert len(executed_calls) == 5
    assert "pg_advisory_xact_lock" in executed_calls[0].args[0]
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in (
        executed_calls[1].args[0]
    )
    assert "SELECT version, name, checksum" in executed_calls[2].args[0]
    assert executed_calls[3] == call(migration_sql)
    assert "INSERT INTO schema_migrations" in executed_calls[4].args[0]
    assert executed_calls[4].args[1] == (
        1,
        "create_example",
        sha256(migration_sql.encode("utf-8")).hexdigest(),
    )
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()
    mock_conn.close.assert_called_once()


def test_create_tables_skips_recorded_migration(
    monkeypatch,
    tmp_path,
):
    """Verify already applied migrations are not run a second time."""
    migration_sql = "CREATE TABLE example (id INTEGER);"
    migration_path = tmp_path / "0001_create_example.sql"
    migration_path.write_text(migration_sql, encoding="utf-8")
    monkeypatch.setattr("app.database.MIGRATIONS_DIR", tmp_path)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (
            1,
            "create_example",
            sha256(migration_sql.encode("utf-8")).hexdigest(),
        )
    ]
    monkeypatch.setattr(
        "app.database.get_connection",
        MagicMock(return_value=mock_conn),
    )

    create_tables()

    assert call(migration_sql) not in mock_cursor.execute.call_args_list
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


def test_create_tables_rejects_changed_applied_migration(
    monkeypatch,
    tmp_path,
):
    """Verify migration checksums prevent editing an applied migration."""
    migration_path = tmp_path / "0001_create_example.sql"
    migration_path.write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr("app.database.MIGRATIONS_DIR", tmp_path)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [(1, "create_example", "wrong")]
    monkeypatch.setattr(
        "app.database.get_connection",
        MagicMock(return_value=mock_conn),
    )

    with pytest.raises(RuntimeError, match="must remain immutable"):
        create_tables()

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once()


def test_create_tables_rolls_back_and_closes_on_failure(
    monkeypatch,
    tmp_path,
):
    """Verify migration failures roll back and still close the connection."""
    migration_path = tmp_path / "0001_create_example.sql"
    migration_path.write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr("app.database.MIGRATIONS_DIR", tmp_path)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = RuntimeError("Migration failure")
    monkeypatch.setattr(
        "app.database.get_connection",
        MagicMock(return_value=mock_conn),
    )

    with pytest.raises(RuntimeError, match="Migration failure"):
        create_tables()

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once