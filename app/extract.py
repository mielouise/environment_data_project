"""Environmental data extraction layer.

Defines the abstraction for environmental data sources and
implements the DMI Observation API client.
"""

from abc import ABC, abstractmethod
from typing import Any

import requests


class SensorDataSource(ABC):
    """Abstract base class for environmental data sources."""

    def __init__(
        self,
        source_id: str,
        source_name: str
    ) -> None:
        """Initialize the data source.

        Args:
            source_id:
                Unique source identifier.

            source_name:
                Human-readable source name.
        """
        self.source_id = source_id
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> dict[str, Any]:
        """Retrieve raw data from the source.

        Returns:
            Raw JSON payload.
        """
        raise NotImplementedError


class DMIDataSource(SensorDataSource):
    """Client for the DMI Meteorological Observation API."""

    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str
    ) -> None:
        """Initialize DMI data source.

        Args:
            source_id:
                Unique source identifier.

            source_name:
                Human-readable source name.

            url:
                DMI API endpoint URL.
        """
        super().__init__(
            source_id=source_id,
            source_name=source_name
        )

        self.url = url

    def fetch(self) -> dict[str, Any]:
        """Retrieve observations from DMI.

        Returns:
            Raw JSON response payload.

        Raises:
            RuntimeError:
                If the request fails.
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