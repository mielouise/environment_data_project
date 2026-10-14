"""Pure transformation functions for DMI observations."""

from datetime import datetime
from typing import Any

from app.constants.parameters import ParameterIds
from app.transform.models import MeasurementDTO, TransformResult

PARAMETER_MAPPING: dict[str, ParameterIds] = {
    "temp_dry": ParameterIds.TEMPERATURE,
    "temp_dew": ParameterIds.TEMP_DEW,
    "temp_mean_past1h": ParameterIds.TEMP_MEAN_PAST_1H,
    "temp_max_past1h": ParameterIds.TEMP_MAX_PAST_1H,
    "temp_min_past1h": ParameterIds.TEMP_MIN_PAST_1H,
    "temp_max_past12h": ParameterIds.TEMP_MAX_PAST_12H,
    "temp_min_past12h": ParameterIds.TEMP_MIN_PAST_12H,
    "temp_grass": ParameterIds.TEMP_GRASS,
    "temp_grass_max_past1h": ParameterIds.TEMP_GRASS_MAX_PAST_1H,
    "temp_grass_mean_past1h": ParameterIds.TEMP_GRASS_MEAN_PAST_1H,
    "temp_grass_min_past1h": ParameterIds.TEMP_GRASS_MIN_PAST_1H,
    "temp_soil": ParameterIds.TEMP_SOIL,
    "temp_soil_max_past1h": ParameterIds.TEMP_SOIL_MAX_PAST_1H,
    "temp_soil_mean_past1h": ParameterIds.TEMP_SOIL_MEAN_PAST_1H,
    "temp_soil_min_past1h": ParameterIds.TEMP_SOIL_MIN_PAST_1H,
    "humidity": ParameterIds.HUMIDITY,
    "humidity_past1h": ParameterIds.HUMIDITY_PAST_1H,
    "pressure": ParameterIds.PRESSURE,
    "pressure_at_sea": ParameterIds.PRESSURE_AT_SEA,
    "wind_dir": ParameterIds.WIND_DIR,
    "wind_dir_past1h": ParameterIds.WIND_DIR_PAST_1H,
    "wind_speed": ParameterIds.WIND_SPEED,
    "wind_speed_past1h": ParameterIds.WIND_SPEED_PAST_1H,
    "wind_gust_always_past1h": ParameterIds.WIND_GUST_ALWAYS_PAST_1H,
    "wind_gust_past10min": ParameterIds.WIND_GUST_PAST_10MIN,
    "wind_gust_last1h": ParameterIds.WIND_GUST_LAST_1H,
    "wind_gust_last3h": ParameterIds.WIND_GUST_LAST_3H,
    "wind_gust_last6h": ParameterIds.WIND_GUST_LAST_6H,
    "wind_max": ParameterIds.WIND_MAX,
    "wind_min_past1h": ParameterIds.WIND_MIN_PAST_1H,
    "wind_min": ParameterIds.WIND_MIN,
    "wind_max_per10min_past1h": ParameterIds.WIND_MAX_PER_10MIN_PAST_1H,
    "precip_past1h": ParameterIds.PRECIP_PAST_1H,
    "precip_past10min": ParameterIds.PRECIP_PAST_10MIN,
    "precip_past1min": ParameterIds.PRECIP_PAST_1MIN,
    "precip_past24h": ParameterIds.PRECIP_PAST_24H,
    "precip_dur_past10min": ParameterIds.PRECIP_DUR_PAST_10MIN,
    "precip_dur_past1h": ParameterIds.PRECIP_DUR_PAST_1H,
    "snow_depth_man": ParameterIds.SNOW_DEPTH_MAN,
    "snow_cover_man": ParameterIds.SNOW_COVER_MAN,
    "visibility": ParameterIds.VISIBILITY,
    "visib_mean_last10min": ParameterIds.VISIB_MEAN_LAST_10MIN,
    "cloud_cover": ParameterIds.CLOUD_COVER,
    "cloud_height": ParameterIds.CLOUD_HEIGHT,
    "weather": ParameterIds.WEATHER,
    "radia_glob": ParameterIds.RADIA_GLOB,
    "radia_glob_past1h": ParameterIds.RADIA_GLOB_PAST_1H,
    "sun_last10min_glob": ParameterIds.SUN_LAST_10MIN_GLOB,
    "sun_last1h_glob": ParameterIds.SUN_LAST_1H_GLOB,
    "leav_hum_dur_past10min": ParameterIds.LEAV_HUM_DUR_PAST_10MIN,
    "leav_hum_dur_past1h": ParameterIds.LEAV_HUM_DUR_PAST_1H,
}
SUPPORTED_DMI_PARAMETER_IDS = tuple(PARAMETER_MAPPING)


def _parse_observed_time(value: Any) -> datetime | None:
    """Parse an API observation timestamp, returning None when invalid."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_measurement_value(value: Any) -> float | None:
    """Parse an API measurement value, returning None when invalid."""
    try:
        return float(value)
    except (ValueError, TypeError, AttributeError):
        return None


def _transform_feature(
    feature: dict[str, Any],
    source_id: str,
) -> tuple[MeasurementDTO | None, str | None]:
    """Convert one DMI observation feature, returning a skip reason."""
    if not isinstance(feature, dict):
        return None, "invalid_feature"
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None, "invalid_properties"

    station_id = properties.get("stationId")
    parameter_name = properties.get("parameterId")
    observed_time = properties.get("observed")
    value = properties.get("value")

    if (
        parameter_name is None
        or station_id is None
        or observed_time is None
        or value is None
    ):
        return None, "missing_required_fields"

    parameter_id = PARAMETER_MAPPING.get(parameter_name)
    if parameter_id is None:
        return None, "unsupported_parameter"

    timestamp = _parse_observed_time(observed_time)
    if timestamp is None:
        return None, "invalid_timestamp"

    parsed_value = _parse_measurement_value(value)
    if parsed_value is None:
        return None, "invalid_value"

    return (
        MeasurementDTO(
            source_id=source_id,
            station_id=str(station_id),
            parameter_id=parameter_id.value,
            timestamp=timestamp,
            value=parsed_value,
        ),
        None,
    )


def transform_dmi_observations_with_report(
    raw_json: dict[str, Any],
    source_id: str,
) -> TransformResult[MeasurementDTO]:
    """Transform observations and count records skipped by reason."""
    measurements = []
    skipped: dict[str, int] = {}
    for feature in raw_json.get("features", []):
        measurement, reason = _transform_feature(feature, source_id)
        if measurement is None:
            if reason is None:
                raise RuntimeError("Skipped observation transformation has no reason.")
            skipped[reason] = skipped.get(reason, 0) + 1
        else:
            measurements.append(measurement)
    return TransformResult(records=measurements, skipped=skipped)


def transform_dmi_observations(
    raw_json: dict[str, Any],
    source_id: str,
) -> list[MeasurementDTO]:
    """Normalize supported observations from a DMI API response."""
    return transform_dmi_observations_with_report(
        raw_json,
        source_id,
    ).records
