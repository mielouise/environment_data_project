"""Unit tests for the central orchestration main module."""

from unittest.mock import patch, MagicMock
from app.main import main


@patch("app.main.get_db_connection")
@patch("app.main.create_tables")
@patch("app.main.DMIDataSource")
@patch("app.main.DMIDataTransformer")
@patch("app.main.MeasurementRepository")
def test_main_pipeline_success(
    mock_repo_cls, mock_trans_cls, mock_source_cls, mock_create_tables, mock_get_conn
):
    """Tests that main executes the full ETL pipeline workflow smoothly."""
    # Setup standard live connection mock architecture
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    # Mock source fetch response elements
    mock_source_instance = MagicMock()
    mock_source_instance.fetch.return_value = {"features": []}
    mock_source_instance.source_id = "DMI-STATION"
    mock_source_instance.source_name = "DMI Name"
    mock_source_cls.return_value = mock_source_instance

    # Mock transformer elements
    mock_trans_instance = MagicMock()
    mock_trans_instance.transform.return_value = []
    mock_trans_cls.return_value = mock_trans_instance

    # Execute orchestrator pipeline logic loop
    main()

    # Verifications ensuring every isolated step was activated
    mock_create_tables.assert_called_once()
    mock_source_instance.fetch.assert_called_once()
    mock_trans_instance.transform.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("app.main.create_tables")
def test_main_pipeline_database_initialization_failure(mock_create_tables):
    """Tests that main exits or handles errors if database setup crashes."""
    mock_create_tables.side_effect = Exception("Schema failure")
    
    with patch("sys.exit") as mock_exit:
        main()
        mock_exit.assert_called_once_with(1)


@patch("app.main.create_tables")
@patch("app.main.DMIDataSource")
def test_main_pipeline_runtime_error_handling(mock_source_cls, mock_create_tables):
    """Tests that main safely catches a RuntimeError during the extract phase."""
    mock_source_instance = MagicMock()
    mock_source_instance.fetch.side_effect = RuntimeError("DMI server is down")
    mock_source_cls.return_value = mock_source_instance

    # Kørsel må ikke crashe hele programmet, men skal håndtere fejlen i en except-blok
    with patch("app.main.get_db_connection") as mock_conn:
        main()
        # Sikrer at forbindelsen lukkes til sidst (i 'finally' blokken)
        mock_conn.return_value.close.assert_called_once()


@patch("app.main.create_tables")
@patch("app.main.DMIDataSource")
def test_main_pipeline_unexpected_exception_handling(mock_source_cls, mock_create_tables):
    """Tests that main safely catches any unexpected Exception during execution."""
    mock_source_instance = MagicMock()
    mock_source_instance.fetch.side_effect = Exception("Unknown critical crash")
    mock_source_cls.return_value = mock_source_instance

    with patch("app.main.get_db_connection") as mock_conn:
        main()
        mock_conn.return_value.close.assert_called_once()
