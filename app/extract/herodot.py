"""Herodot observations API data source."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import requests

from app.extract.base import SensorDataSource


class HerodotDataSource(SensorDataSource):
    """Client for the Herodot observations API using Bearer authentication."""

    REQUEST_TIMEOUT_SECONDS = 10
    DEFAULT_URL = "https://herodot.spac.dk/api/v1/observations"

    @classmethod
    def from_environment(
        cls,
        source_id: str = "HERODOT",
        source_name: str = "Herodot Sensor API",
    ) -> HerodotDataSource:
        """Create a source from the Herodot environment configuration.

        Args:
            source_id: Unique identifier for this data source.
            source_name: Human-readable name for this data source.

        Raises:
            RuntimeError: If `SENSOR_API_TOKEN` is not configured.
        """
        api_token = os.environ.get("SENSOR_API_TOKEN")
        if not api_token:
            raise RuntimeError("SENSOR_API_TOKEN environment variable is missing.")

        return cls(
            source_id=source_id,
            source_name=source_name,
            api_token=api_token,
            url=os.environ.get("SENSOR_API_URL", cls.DEFAULT_URL),
        )

    def __init__(
        self,
        source_id: str,
        source_name: str,
        api_token: str,
        url: str = DEFAULT_URL,
    ) -> None:
        """Initialize the source with its endpoint and Bearer token.

        Args:
            source_id: Unique identifier for this data source.
            source_name: Human-readable name for this data source.
            api_token: Secret Bearer token.
            url: Observations endpoint URL.

        Raises:
            ValueError: If the API token is empty.
        """
        super().__init__(source_id=source_id, source_name=source_name)
        if not api_token.strip():
            raise ValueError("Herodot API token must not be empty.")

        self.api_token = api_token
        self.url = url

    def fetch(
        self,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        """Fetch the raw observations response from Herodot.

        Args:
            params: Optional query parameters.

        Returns:
            Raw JSON object returned by the API.

        Raises:
            RuntimeError: If the request fails or the response is not a JSON
                object.
        """
        request_options: dict[str, Any] = {
            "headers": {"Authorization": f"Bearer {self.api_token}"},
            "timeout": self.REQUEST_TIMEOUT_SECONDS,
        }
        if params is not None:
            request_options["params"] = params

        try:
            response = requests.get(self.url, **request_options)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as err:
            raise RuntimeError(f"Failed to retrieve Herodot data: {err}") from err
        except ValueError as err:
            raise RuntimeError("Herodot API returned invalid JSON.") from err

        if not isinstance(payload, dict):
            raise RuntimeError("Herodot API response must be a JSON object.")
        return payload
