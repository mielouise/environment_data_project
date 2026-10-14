"""Pure normalization of DMI station versions and geographic locations."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StationDTO:
    station_id: str
    station_name: str | None
    latitude: float | None
    longitude: float | None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    station_type: str | None = None
    station_status: str | None = None
    country: str | None = None
    owner: str | None = None
    station_height: float | None = None


def parse_utc_timestamp(value: Any) -> datetime | None:
    """Parse DMI validity timestamps; missing values indicate unknown history."""
    if not isinstance(value, str) or not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def transform_station(feature: dict[str, Any]) -> StationDTO | None:
    """Normalize one station metadata version."""
    properties = feature.get("properties") or {}
    identifier = properties.get("stationId")
    if identifier is None:
        return None
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    longitude = latitude = None
    if geometry.get("type") == "Point" and len(coordinates) >= 2:
        longitude, latitude = parse_number(coordinates[0]), parse_number(coordinates[1])
    valid_from = parse_utc_timestamp(properties.get("validFrom"))
    valid_to = parse_utc_timestamp(properties.get("validTo"))
    return StationDTO(
        station_id=str(identifier),
        station_name=properties.get("name"),
        latitude=latitude,
        longitude=longitude,
        valid_from=valid_from,
        valid_to=valid_to,
        station_type=properties.get("type"),
        station_status=properties.get("status"),
        country=properties.get("country"),
        owner=properties.get("owner"),
        station_height=parse_number(properties.get("height")),
    )


def transform_stations(payload: dict[str, Any]) -> list[StationDTO]:
    """Keep every returned station version instead of collapsing by stationId."""
    result: list[StationDTO] = []
    for feature in payload.get("features", []):
        station = transform_station(feature)
        if station is not None:
            result.append(station)
    return result
