"""Module for extracting raw environmental data from external sources.

This module implements the abstraction layer for data ingestion. It defines
a common interface for all future hardware sensors and web APIs, and provides
the specific implementation for fetching open-access weather data from DMI.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union
import requests


class SensorDataSource(ABC):
    """Abstract Base Class defining the interface for all environmental data inputs.

    Acts as a contract ensuring that any future hardware components or API integration
    services implement a unified extraction methodology.

    Attributes:
        source_id: Unique alphanumeric identifier for the data source.
        source_name: User-friendly name describing the physical sensor or API endpoint.
    """

    def __init__(self, source_id: str, source_name: str) -> None:
        """Initializes the base data source components.

        Args:
            source_id: Unique identifier for the reporting entity.
            source_name: Human-readable name or label for the source.
        """
        self.source_id = source_id
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> Union[Dict[str, Any], list]:
        """Fetches raw data payload from the designated origin channel.

        This method must be overridden by specific subclass implementations.

        Returns:
            The raw data structures, typically a dictionary or an array of packets.

        Raises:
            RuntimeError: If data retrieval encounters an infrastructure failure.
        """
        pass


class DMIDataSource(SensorDataSource):
    """Data source implementation targeting DMI's open meteorological Web API.

    Handles network connectivity and ensures graceful exceptions when querying the public
    observation server endpoints.
    """

    def __init__(self, source_id: str, source_name: str, url: str) -> None:
        """Initializes the DMI data source with connection endpoints.

        Args:
            source_id: Unique station identifier.
            source_name: Name of the geographical area or station.
            url: Full URL string endpoint targeting the open data REST API.
        """
        super().__init__(source_id, source_name)
        self.url = url

    def fetch(self) -> Dict[str, Any]:
        """Queries the open DMI API endpoint to gather recent climate records.

        Enforces safe HTTP request behaviors by setting strict timeout rules.

        Returns:
            A dictionary containing raw GeoJSON spatial observation elements.

        Raises:
            RuntimeError: Wrapped connection/protocol errors indicating a down API.
        """
        try:
            # Set a 10-second request timeout to prevent blocking application pipelines
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            
            # Explicitly cast response data structure as a dictionary payload
            raw_payload: Dict[str, Any] = response.json()
            return raw_payload
            
        except requests.RequestException as err:
            # Clean Code: Translate technical low-level stack errors into explicit messages
            raise RuntimeError(f"Kunne ikke hente data fra DMI: {err}") from err
