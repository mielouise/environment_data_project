"""Small, testable station normalization functions."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StationDTO:
    station_id: str
    station_name: str | None
    latitude: float | None
    longitude: float | None


def transform_station(feature: dict[str, Any]) -> StationDTO | None:
    properties = feature.get("properties") or {}
    identifier = properties.get("stationId")
    if identifier is None:
        return None
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    longitude = latitude = None
    if geometry.get("type") == "Point" and len(coordinates) >= 2:
        try:
            longitude, latitude = float(coordinates[0]), float(coordinates[1])
        except (ValueError, TypeError):
            longitude = latitude = None
    return StationDTO(str(identifier), properties.get("name"), latitude, longitude)


def transform_stations(payload: dict[str, Any]) -> list[StationDTO]:
    result = []
    for feature in payload.get("features", []):
        station = transform_station(feature)
        if station is not None:
            result.append(station)
    return result
