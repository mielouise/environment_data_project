"""Integration tests for the DMI Observation API."""

import os

from app.extract import DMIDataSource


def test_dmi_api_connection():
    """Verify the configured DMI endpoint returns observation data."""

    source = DMIDataSource(
        source_id="DMI",
        source_name="DMI Observation API",
        url=os.environ["DMI_API_URL"],
    )

    response = source.fetch()

    assert isinstance(response, dict)
    assert "features" in response
