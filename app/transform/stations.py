"""DMI station transformation functions."""

from datetime import datetime
from typing import Any

from app.transform.models import StationDTO


def _transform_station(feature: dict[str, Any]) -> StationDTO | None:
    """Convert one valid GeoJSON station feature to a DTO."""
    properties = feature.get("properties", {})
    station_id = properties.get("stationId")
    name = properties.get("name")
    station_type = properties.get("type")
    country_code = properties.get("country")
    coordinates = feature.get("geometry", {}).get("coordinates")
    valid_from = properties.get("validFrom")

    if (
        station_id is None
        or name is None
        or station_type is None
        or country_code is None
        or not isinstance(coordinates, list)
        or len(coordinates) < 2
        or valid_from is None
    ):
        return None

    try:
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        station_height = properties.get("stationHeight")
        parsed_height = (
            None if station_height is None else float(station_height)
        )
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            return None
        return StationDTO(
            station_id=str(station_id),
            name=str(name),
            station_type=str(station_type),
            country_code=str(country_code),
            latitude=latitude,
            longitude=longitude,
            station_height=parsed_height,
            valid_from=datetime.fromisoformat(
                valid_from.replace("Z", "+00:00")
            ),
        )
    except (ValueError, TypeError, AttributeError):
        return None


def transform_dmi_stations(raw_json: dict[str, Any]) -> list[StationDTO]:
    """Normalize station features, keeping the newest version per station."""
    stations_by_id: dict[str, StationDTO] = {}
    for feature in raw_json.get("features", []):
        station = _transform_station(feature)
        if station is None:
            continue
        current = stations_by_id.get(station.station_id)
        if current is None or station.valid_from > current.valid_from:
            stations_by_id[station.station_id] = station
    return sorted(
        stations_by_id.values(),
        key=lambda station: station.station_id,
    )
