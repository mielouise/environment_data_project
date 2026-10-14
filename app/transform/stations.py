"""DMI station transformation functions."""

from datetime import datetime
from typing import Any

from app.transform.models import StationDTO, TransformResult


def _parse_coordinates(
    geometry: Any,
) -> tuple[float, float] | None:
    """Parse and validate GeoJSON longitude and latitude."""
    if not isinstance(geometry, dict):
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    try:
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
    except (ValueError, TypeError, AttributeError):
        return None
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        return None
    return longitude, latitude


def _parse_station_height(properties: dict[str, Any]) -> float | None:
    """Parse an optional station height, returning None when absent or invalid."""
    height = properties.get("stationHeight")
    if height is None:
        return None
    try:
        return float(height)
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_valid_from(value: Any) -> datetime | None:
    """Parse a station validity timestamp, returning None when invalid."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _transform_station(
    feature: dict[str, Any],
) -> tuple[StationDTO | None, str | None]:
    """Convert one GeoJSON feature, returning a skip reason."""
    if not isinstance(feature, dict):
        return None, "invalid_feature"
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None, "invalid_properties"

    station_id = properties.get("stationId")
    name = properties.get("name")
    station_type = properties.get("type")
    country_code = properties.get("country")
    parsed_coordinates = _parse_coordinates(feature.get("geometry"))
    valid_from = _parse_valid_from(properties.get("validFrom"))

    if (
        station_id is None
        or name is None
        or station_type is None
        or country_code is None
    ):
        return None, "missing_required_fields"

    if parsed_coordinates is None:
        return None, "invalid_coordinates"
    longitude, latitude = parsed_coordinates

    station_height = properties.get("stationHeight")
    parsed_height = _parse_station_height(properties)
    if station_height is not None and parsed_height is None:
        return None, "invalid_station_height"

    if valid_from is None:
        return None, "invalid_valid_from"

    return (
        StationDTO(
            station_id=str(station_id),
            name=str(name),
            station_type=str(station_type),
            country_code=str(country_code),
            latitude=latitude,
            longitude=longitude,
            station_height=parsed_height,
            valid_from=valid_from,
        ),
        None,
    )


def transform_dmi_stations_with_report(
    raw_json: dict[str, Any],
) -> TransformResult[StationDTO]:
    """Transform station metadata and count skipped versions by reason."""
    stations_by_id: dict[str, StationDTO] = {}
    skipped: dict[str, int] = {}
    for feature in raw_json.get("features", []):
        station, reason = _transform_station(feature)
        if station is None:
            if reason is None:
                raise RuntimeError("Skipped station transformation has no reason.")
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        current = stations_by_id.get(station.station_id)
        if current is None:
            stations_by_id[station.station_id] = station
        else:
            skipped["superseded_station_version"] = (
                skipped.get("superseded_station_version", 0) + 1
            )
            if station.valid_from > current.valid_from:
                stations_by_id[station.station_id] = station
    stations = sorted(
        stations_by_id.values(),
        key=lambda station: station.station_id,
    )
    return TransformResult(records=stations, skipped=skipped)


def transform_dmi_stations(raw_json: dict[str, Any]) -> list[StationDTO]:
    """Normalize station features, keeping the newest version per station."""
    return transform_dmi_stations_with_report(raw_json).records
