"""Unit tests for migration discovery and execution."""

from hashlib import sha256
from pathlib import Path
import re
from unittest.mock import MagicMock, call

import pytest

from app.constants.parameters import ParameterIds
from app.migration_runner import apply_migrations
from app.transform.dmi import PARAMETER_MAPPING


def _prepare_migration(monkeypatch, tmp_path, migration_sql="SELECT 1;"):
    migration_path = tmp_path / "0001_create_example.sql"
    migration_path.write_text(migration_sql, encoding="utf-8")
    monkeypatch.setattr("app.migration_runner.MIGRATIONS_DIR", tmp_path)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    monkeypatch.setattr(
        "app.migration_runner.get_connection",
        MagicMock(return_value=mock_conn),
    )
    return mock_conn, mock_cursor, migration_sql


def test_dmi_parameter_ids_match_seed_migration():
    migration = (
        Path(__file__).parents[2]
        / "app"
        / "migrations"
        / "0003_dmi_observation_parameters.sql"
    ).read_text(encoding="utf-8")
    seeded_parameters = {
        name: int(parameter_id)
        for parameter_id, name in re.findall(
            r"\((\d+),\s*'([^']+)',\s*'[^']+'\)",
            migration,
        )
    }

    for name, parameter_id in PARAMETER_MAPPING.items():
        if parameter_id.value > 3:
            assert seeded_parameters[name] == parameter_id.value
        assert ParameterIds(parameter_id.value) == parameter_id


def test_apply_migrations_applies_and_records_pending_migration(
    monkeypatch,
    tmp_path,
):
    mock_conn, mock_cursor, migration_sql = _prepare_migration(
        monkeypatch,
        tmp_path,
        "CREATE TABLE example (id INTEGER);",
    )

    apply_migrations()

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


def test_apply_migrations_skips_recorded_migration(monkeypatch, tmp_path):
    mock_conn, mock_cursor, migration_sql = _prepare_migration(
        monkeypatch,
        tmp_path,
    )
    mock_cursor.fetchall.return_value = [
        (
            1,
            "create_example",
            sha256(migration_sql.encode("utf-8")).hexdigest(),
        )
    ]

    apply_migrations()

    assert call(migration_sql) not in mock_cursor.execute.call_args_list
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


def test_apply_migrations_rejects_changed_applied_migration(
    monkeypatch,
    tmp_path,
):
    mock_conn, mock_cursor, _ = _prepare_migration(
        monkeypatch,
        tmp_path,
    )
    mock_cursor.fetchall.return_value = [(1, "create_example", "wrong")]

    with pytest.raises(RuntimeError, match="must remain immutable"):
        apply_migrations()

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once()


def test_apply_migrations_rolls_back_and_closes_on_failure(
    monkeypatch,
    tmp_path,
):
    mock_conn, mock_cursor, _ = _prepare_migration(
        monkeypatch,
        tmp_path,
    )
    mock_cursor.execute.side_effect = RuntimeError("Migration failure")

    with pytest.raises(RuntimeError, match="Migration failure"):
        apply_migrations()

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once()
