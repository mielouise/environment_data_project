"""DMI station transformation functions."""

from datetime import datetime
from typing import Any

from app.transform.models import StationDTO, TransformResult


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
    geometry = feature.get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(
        geometry,
        dict,
    ) else None
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
        return None, "missing_required_fields"

    try:
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            return None, "invalid_coordinates"
    except (ValueError, TypeError, AttributeError):
        return None, "invalid_coordinates"

    try:
        station_height = properties.get("stationHeight")
        parsed_height = (
            None if station_height is None else float(station_height)
        )
    except (ValueError, TypeError, AttributeError):
        return None, "invalid_station_height"

    try:
        station = StationDTO(
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
        return None, "invalid_valid_from"
    return station, None


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
                raise RuntimeError(
                    "Skipped station transformation has no reason."
                )
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
