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


@patch("app.main.create_tables")
def test_run_once_requires_url(migrate, monkeypatch):
    monkeypatch.delenv("DMI_API_URL", raising=False)
    with pytest.raises(RuntimeError, match="DMI_API_URL"):
        run_once()
    migrate.assert_not_called()


@patch("app.main.create_tables")
def test_run_once_rejects_invalid_lookback(migrate, monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "https://example.test")
    monkeypatch.setenv("DMI_LOOKBACK_MINUTES", "0")
    with pytest.raises(ValueError, match="positive"):
        run_once()
    migrate.assert_not_called()


@patch("app.main.create_tables")
def test_run_once_rejects_empty_parameter_selection(migrate, monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "https://example.test")
    monkeypatch.setenv("DMI_LOOKBACK_MINUTES", "60")
    monkeypatch.setenv("DMI_PARAMETER_IDS", ", ,")
    with pytest.raises(ValueError, match="requires at least"):
        run_once()


@patch("app.main.run_weather_pipeline", side_effect=RuntimeError("failed"))
@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
def test_run_once_rolls_back_and_closes(migrate, conn_factory, pipeline, monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "https://example.test")
    monkeypatch.setenv("DMI_PARAMETER_IDS", "temp_dry")
    monkeypatch.setenv("DMI_LOOKBACK_MINUTES", "60")
    with pytest.raises(RuntimeError, match="failed"):
        run_once()
    conn_factory.return_value.rollback.assert_called_once()
    conn_factory.return_value.close.assert_called_once()


@patch("app.main.run_weather_pipeline", return_value=2)
@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
def test_run_once_without_stations(migrate, conn_factory, pipeline, monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "https://example.test")
    monkeypatch.setenv("DMI_PARAMETER_IDS", "temp_dry")
    monkeypatch.setenv("DMI_LOOKBACK_MINUTES", "60")
    monkeypatch.setenv("DMI_FETCH_STATIONS", "false")
    monkeypatch.setenv("DMI_STATION_ID", "06030")
    assert run_once() == 2
    assert pipeline.call_args.kwargs["station_source"] is None
    assert pipeline.call_args.kwargs["params"]["stationId"] == "06030"


def test_main_rejects_negative_poll_interval(monkeypatch):
    monkeypatch.setenv("DMI_POLL_SECONDS", "-1")
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
