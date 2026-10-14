"""Base abstraction for environmental data sources."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class SensorDataSource(ABC):
    """Abstract base class for environmental data sources.

    All environmental data providers must implement the
    fetch method to return raw data.
    """

    def __init__(self, source_id: str, source_name: str) -> None:
        """Initialize the data source.

        Args:
            source_id:
                Unique identifier of the data source.

            source_name:
                Human-readable name of the data source.
        """
        self.source_id = source_id
        self.source_name = source_name

    @abstractmethod
    def fetch(
        self,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        """Fetch raw data from the source.

        Args:
            params:
                Optional request query parameters.

        Returns:
            Raw JSON-compatible payload.
        """
        raise NotImplementedError
