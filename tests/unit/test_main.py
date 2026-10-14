"""Unit tests for the application entry point."""

from unittest.mock import MagicMock, patch

import pytest

from app.main import (
    DEFAULT_DMI_PARAMETER_IDS,
    _configured_parameter_ids,
    main,
    run_continuously,
)


@patch("app.main.apply_migrations")
@patch("app.main.DMIDataSource")
@patch("app.main.run_dmi_pipeline", return_value=2)
def test_main_pipeline_success(
    mock_run_pipeline,
    mock_source_cls,
    mock_apply_migrations,
    monkeypatch,
):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.delenv("ETL_INTERVAL_SECONDS", raising=False)
    mock_source = MagicMock()
    mock_station_source = MagicMock()
    mock_source_cls.side_effect = [mock_source, mock_station_source]

    main()

    mock_apply_migrations.assert_called_once_with()
    assert mock_source_cls.call_args_list[0].kwargs == {
        "source_id": "DMI",
        "source_name": "DMI Observation API",
        "url": (
            "http://fake-url.com/v2/metObs/collections/"
            "observation/items"
        ),
    }
    assert mock_source_cls.call_args_list[1].kwargs["source_id"] == (
        "DMI_STATIONS"
    )
    assert mock_source_cls.call_args_list[1].kwargs["url"] == (
        "http://fake-url.com/v2/metObs/collections/station/items"
    )
    mock_run_pipeline.assert_called_once_with(
        observation_source=mock_source,
        station_source=mock_station_source,
        parameter_ids=DEFAULT_DMI_PARAMETER_IDS,
    )


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
    monkeypatch.delenv("ETL_INTERVAL_SECONDS", raising=False)

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
    monkeypatch.delenv("ETL_INTERVAL_SECONDS", raising=False)
    mock_run_pipeline.side_effect = RuntimeError("DMI server is down")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_continuous_execution_retries_after_failure(monkeypatch, caplog, capsys):
    run_once = MagicMock(side_effect=[RuntimeError("temporary"), 1])
    sleep = MagicMock()

    def stop_after_second_sleep(interval):
        if sleep.call_count == 2:
            raise KeyboardInterrupt

    sleep.side_effect = stop_after_second_sleep
    monkeypatch.setattr("app.main.time.sleep", sleep)

    with pytest.raises(KeyboardInterrupt):
        run_continuously(run_once, 60)

    assert run_once.call_count == 2
    assert sleep.call_count == 2
    assert "Pipeline execution failed; it will be retried." in caplog.text
    assert "ETL cycle completed: 1 observations processed." in (
        capsys.readouterr().out
    )


def test_main_enables_continuous_execution_from_environment(monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.setenv("ETL_INTERVAL_SECONDS", "300")
    monkeypatch.setattr("app.main.apply_migrations", MagicMock())
    run_continuously_mock = MagicMock()
    monkeypatch.setattr(
        "app.main.run_continuously",
        run_continuously_mock,
    )

    main()

    run_continuously_mock.assert_called_once()
    assert callable(run_continuously_mock.call_args.args[0])
    assert run_continuously_mock.call_args.args[1] == 300


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
        "wind_speed",
        "precip_past1h",
    )
    assert _configured_parameter_ids() == DEFAULT_DMI_PARAMETER_IDS


def test_main_rejects_unsupported_dmi_parameters(monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    monkeypatch.setenv("DMI_PARAMETER_IDS", "not_a_dmi_parameter")
    monkeypatch.setattr("app.main.apply_migrations", MagicMock())

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@pytest.mark.parametrize("interval", [0, -1, float("inf"), float("nan")])
def test_continuous_execution_requires_positive_interval(interval):
    with pytest.raises(ValueError, match="greater than zero"):
        run_continuously(MagicMock(), interval)


def test_main_rejects_nonpositive_interval(monkeypatch):
    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")

    with pytest.raises(SystemExit) as exc_info:
        main(["--interval-seconds", "0"])

    assert exc_info.value.code == 2
