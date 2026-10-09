"""Unit tests for the central orchestration main module."""

from unittest.mock import MagicMock, patch

import pytest

from app.main import main


@patch("app.main.create_tables")
@patch("app.main.DMIDataSource")
@patch("app.main.DMIDataTransformer")
@patch("app.main.MeasurementRepository")
@patch("app.main.ETLService")
@patch("app.main.get_db_connection")
def test_main_pipeline_success(
    mock_get_conn,
    mock_etl_service_cls,
    mock_repo_cls,
    mock_trans_cls,
    mock_source_cls,
    mock_create_tables,
    monkeypatch,
):
    """Verify main wires the ETL service and closes its connection."""

    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn

    mock_source_instance = MagicMock()
    mock_source_instance.source_id = "DMI-STATION"
    mock_source_instance.source_name = "DMI Observation API"
    mock_source_cls.return_value = mock_source_instance

    mock_trans_instance = MagicMock()
    mock_trans_cls.return_value = mock_trans_instance

    mock_repo_instance = MagicMock()
    mock_repo_cls.return_value = mock_repo_instance
    mock_service_instance = MagicMock()
    mock_service_instance.run.return_value = 2
    mock_etl_service_cls.return_value = mock_service_instance

    main()

    mock_create_tables.assert_called_once()
    mock_source_cls.assert_called_once_with(
        source_id="DMI",
        source_name="DMI Observation API",
        url="http://fake-url.com",
    )
    mock_trans_cls.assert_called_once_with(
        source_id="DMI-STATION"
    )
    mock_get_conn.assert_called_once_with()
    mock_repo_cls.assert_called_once_with(mock_conn)
    mock_etl_service_cls.assert_called_once_with(
        source=mock_source_instance,
        transformer=mock_trans_instance,
        repository=mock_repo_instance,
    )
    mock_service_instance.run.assert_called_once_with()
    mock_conn.close.assert_called_once()


@patch("app.main.create_tables")
def test_main_pipeline_database_initialization_failure(mock_create_tables):
    """Verify a database initialization error terminates the pipeline."""

    mock_create_tables.side_effect = Exception("Schema failure")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
def test_main_requires_dmi_api_url(
    mock_create_tables,
    mock_get_conn,
    monkeypatch,
):
    """Verify missing endpoint configuration stops before connecting."""

    monkeypatch.delenv("DMI_API_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    mock_create_tables.assert_called_once_with()
    mock_get_conn.assert_not_called()


@patch("app.main.ETLService")
@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
def test_main_pipeline_runtime_error_closes_connection(
    mock_create_tables,
    mock_get_conn,
    mock_etl_service_cls,
    monkeypatch,
):
    """Verify ETL errors exit and release the database connection."""

    monkeypatch.setenv("DMI_API_URL", "http://fake-url.com")
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_etl_service_cls.return_value.run.side_effect = RuntimeError(
        "DMI server is down"
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    mock_conn.close.assert_called_once()
