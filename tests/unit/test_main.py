"""Unit tests for the application entry point."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.main import (
    DEFAULT_DMI_PARAMETER_IDS,
    _configured_parameter_ids,
    main,
)


@patch("app.main.apply_migrations")
@patch("app.main.DMIDataSource")
@patch("app.main.run_dmi_pipeline", return_value=2)
def test_main_pipeline_success(
    mock_run_pipeline,
    mock_source_cls,
    mock_apply_migrations,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.delenv("DMI_PARAMETER_IDS", raising=False)
    monkeypatch.setenv("HERODOT_ENABLED", "false")
    configure_logging = MagicMock()
    monkeypatch.setattr("app.main.logging.basicConfig", configure_logging)
    mock_source = MagicMock()
    mock_station_source = MagicMock()
    mock_source_cls.side_effect = [mock_source, mock_station_source]

    main()

    configure_logging.assert_called_once_with(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mock_apply_migrations.assert_called_once_with()
    assert mock_source_cls.call_args_list[0].kwargs == {
        "source_id": "DMI",
        "source_name": "DMI Observation API",
        "url": ("http://fake-url.com/v2/metObs/collections/observation/items"),
    }
    assert mock_source_cls.call_args_list[1].kwargs["source_id"] == ("DMI_STATIONS")
    assert mock_source_cls.call_args_list[1].kwargs["url"] == (
        "http://fake-url.com/v2/metObs/collections/station/items"
    )
    mock_run_pipeline.assert_called_once_with(
        observation_source=mock_source,
        station_source=mock_station_source,
        parameter_ids=DEFAULT_DMI_PARAMETER_IDS,
    )
    assert "ETL cycle completed: 2 observations processed." in (capsys.readouterr().out)


@patch("app.main.apply_migrations")
@patch("app.main.DMIDataSource")
@patch("app.main.run_dmi_pipeline", return_value=2)
@patch("app.main.HerodotDataSource.from_environment")
@patch("app.main.run_herodot_pipeline", return_value=45)
def test_main_runs_herodot_when_enabled(
    mock_run_herodot,
    mock_herodot_source,
    mock_run_dmi,
    mock_dmi_source,
    mock_apply_migrations,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.setenv("HERODOT_ENABLED", "true")
    mock_dmi_source.side_effect = [MagicMock(), MagicMock()]
    source = MagicMock()
    mock_herodot_source.return_value = source

    main()

    mock_herodot_source.assert_called_once_with()
    mock_run_herodot.assert_called_once_with(source)
    output = capsys.readouterr().out
    assert "ETL cycle completed: 2 observations processed." in output
    assert "Herodot cycle completed: 45 measurements processed" in output


@patch("app.main.apply_migrations")
def test_main_pipeline_database_initialization_failure(mock_apply_migrations):
    mock_apply_migrations.side_effect = Exception("Schema failure")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("app.main.apply_migrations")
def test_main_requires_dmi_api_url(
    mock_apply_migrations,
    monkeypatch,
):
    monkeypatch.delenv("DMI_API_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    mock_apply_migrations.assert_not_called()


@patch("app.main.run_dmi_pipeline")
@patch("app.main.apply_migrations")
def test_main_pipeline_runtime_error_exits_with_failure_status(
    mock_apply_migrations,
    mock_run_pipeline,
    monkeypatch,
):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    mock_run_pipeline.side_effect = RuntimeError("DMI server is down")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_main_uses_configured_dmi_parameters(monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.setenv("DMI_PARAMETER_IDS", "temp_dry,humidity")
    monkeypatch.setattr("app.main.apply_migrations", MagicMock())
    pipeline_mock = MagicMock(return_value=0)
    monkeypatch.setattr("app.main.run_dmi_pipeline", pipeline_mock)

    main()

    assert pipeline_mock.call_args.kwargs["parameter_ids"] == (
        "temp_dry",
        "humidity",
    )


def test_configured_dmi_parameters_defaults_to_selected_categories(
    monkeypatch,
):
    monkeypatch.delenv("DMI_PARAMETER_IDS", raising=False)

    assert DEFAULT_DMI_PARAMETER_IDS == (
        "temp_dry",
        "humidity",
    )
    assert _configured_parameter_ids() == DEFAULT_DMI_PARAMETER_IDS


def test_main_rejects_unsupported_dmi_parameters(monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.setenv("DMI_PARAMETER_IDS", "not_a_dmi_parameter")
    monkeypatch.setattr("app.main.apply_migrations", MagicMock())

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
