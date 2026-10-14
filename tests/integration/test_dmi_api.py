"""Integration tests for the DMI Observation API."""

import os
from datetime import datetime, timedelta, timezone

from app.extract import DMIDataSource
from app.extract.dmi import build_dmi_collection_url


def test_dmi_api_connection():
    """Verify the configured DMI endpoint returns observation data."""

    source = DMIDataSource(
        source_id="DMI",
        source_name="DMI Observation API",
        url=build_dmi_collection_url(
            os.environ["DMI_API_URL"],
            "observation",
        ),
    )

    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=5)
    response = source.fetch(
        params={
            "parameterId": "temp_dry",
            "datetime": (
                f"{start.isoformat().replace('+00:00', 'Z')}/"
                f"{now.isoformat().replace('+00:00', 'Z')}"
            ),
            "limit": 1000,
        }
    )

    assert isinstance(response, dict)
    assert "features" in response
