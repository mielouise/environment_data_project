"""Entry-point tests."""
from unittest.mock import MagicMock, patch
import pytest
from app.main import main, run_once


@patch("app.main.run_once", return_value=2)
def test_main_once(mock_run, monkeypatch):
    monkeypatch.setenv("DMI_POLL_SECONDS", "0")
    main()
    mock_run.assert_called_once()


@patch("app.main.run_once", side_effect=RuntimeError("down"))
def test_main_exits_on_failure(mock_run, monkeypatch):
    monkeypatch.setenv("DMI_POLL_SECONDS", "0")
    with pytest.raises(SystemExit) as err:
        main()
    assert err.value.code == 1


@patch("app.main.run_weather_pipeline", return_value=2)
@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
def test_run_once_closes_connection(migrate, connection, run, monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://example.test")
    connection.return_value = MagicMock()
    assert run_once() == 2
    connection.return_value.close.assert_called_once()
    migrate.assert_called_once()
