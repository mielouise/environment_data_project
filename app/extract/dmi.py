"""DMI GeoJSON API client with bounded pagination and request filtering."""
from typing import Any
import requests
from app.extract.base import SensorDataSource


class DMIDataSource(SensorDataSource):
    REQUEST_TIMEOUT_SECONDS = 10

    def __init__(self, source_id: str, source_name: str, url: str) -> None:
        super().__init__(source_id, source_name)
        self.url = url

    def fetch(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Request all pages, preserving the original GeoJSON envelope."""
        requested = dict(params or {})
        limit = int(requested.get("limit", 1000))
        if limit < 1:
            raise ValueError("limit must be positive")
        requested["limit"] = limit
        offset = int(requested.get("offset", 0))
        features = []
        try:
            while True:
                requested["offset"] = offset
                response = requests.get(
                    self.url, params=requested,
                    timeout=self.REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not isinstance(data.get("features"), list):
                    raise ValueError("Unexpected DMI response structure")
                page = data["features"]
                features.extend(page)
                if len(page) < limit:
                    break
                offset += len(page)
                # Prevent unbounded extraction from a misconfigured endpoint.
                if offset >= 100000:
                    raise RuntimeError("DMI pagination safety limit reached")
            return {"type": "FeatureCollection", "features": features}
        except (requests.RequestException, ValueError) as err:
            raise RuntimeError(f"Failed to retrieve DMI data: {err}") from err
