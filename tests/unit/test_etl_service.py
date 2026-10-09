"""Unit tests for ETL workflow orchestration."""

from unittest.mock import MagicMock

import pytest

from app.etl_service import ETLService


def test_run_extracts_transforms_and_persists_measurements():
    """Verify the service saves source metadata and transformed records."""

    source = MagicMock()
    source.source_id = "DMI"
    source.source_name = "DMI Observation API"
    raw_data = {"features": []}
    source.fetch.return_value = raw_data

    transformer = MagicMock()
    measurements = [MagicMock(), MagicMock()]
    transformer.transform.return_value = measurements

    repository = MagicMock()
    service = ETLService(
        source=source,
        transformer=transformer,
        repository=repository,
    )

    assert service.run() == 2

    source.fetch.assert_called_once_with()
    transformer.transform.assert_called_once_with(raw_data)
    repository.save_source.assert_called_once_with(
        source_id="DMI",
        source_name="DMI Observation API",
        source_type="API_DMI",
    )
    repository.save_measurements.assert_called_once_with(measurements)


def test_run_propagates_fetch_errors_without_persisting():
    """Verify extraction failures propagate before repository writes."""

    source = MagicMock()
    source.fetch.side_effect = RuntimeError("DMI server is down")
    transformer = MagicMock()
    repository = MagicMock()
    service = ETLService(
        source=source,
        transformer=transformer,
        repository=repository,
    )

    with pytest.raises(RuntimeError, match="DMI server is down"):
        service.run()

    transformer.transform.assert_not_called()
    repository.save_source.assert_not_called()
    repository.save_measurements.assert_not_called()
