"""DMI Observation API data source."""

from typing import Any

import requests

from app.extract.base import SensorDataSource


class DMIDataSource(SensorDataSource):
    """Client for the DMI Meteorological Observation API."""

    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str
    ) -> None:
        """Initialize the DMI data source.

        Args:
            source_id:
                Unique identifier of the source.

            source_name:
                Human-readable name of the source.

            url:
                DMI Observation API endpoint URL.
        """
        super().__init__(
            source_id=source_id,
            source_name=source_name
        )

        self.url = url

    def fetch(self) -> dict[str, Any]:
        """Retrieve observations from the DMI API.

        Returns:
            Dictionary containing the raw API response.

        Raises:
            RuntimeError:
                Raised when the API request fails.
        """
        try:
            response = requests.get(
                self.url,
                timeout=self.REQUEST_TIMEOUT_SECONDS
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as err:
            raise RuntimeError(
                f"Failed to retrieve DMI data: {err}"
            ) from err
