"""Environmental data extraction layer.

Defines the abstraction for all environmental data sources and
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
        """Fetch data from the source.

        Returns:
            Raw JSON payload.
        """
        raise NotImplementedError


class DMIDataSource(SensorDataSource):
    """Client for the DMI Meteorological Observation API."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        url: str
    ) -> None:
        """Initialize DMI data source.

        Args:
            source_id:
                Source identifier.

            source_name:
                Human-readable source name.

            url:
                DMI API endpoint.
        """
        super().__init__(
            source_id=source_id,
            source_name=source_name
        )
        self.url = url

    def fetch(self) -> dict[str, Any]:
        """Fetch raw observations from DMI.

        Returns:
            Raw JSON response from the API.

        Raises:
            RuntimeError:
                If the HTTP request fails.
        """
        try:
            response = requests.get(
                self.url,
                timeout=10
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as err:
            raise RuntimeError(
                f"Failed to retrieve DMI data: {err}"
            ) from err