"""Transform Herodot observations into the shared measurement model."""

import math
from datetime import datetime
from typing import Any

from app.constants.parameters import ParameterIds
from app.transform.models import MeasurementDTO, TransformResult

HERODOT_SENSOR_PARAMETERS = {
    "temperature": ParameterIds.TEMPERATURE,
    "humidity": ParameterIds.HUMIDITY,
    "pressure": ParameterIds.PRESSURE,
    "co2_concentration": ParameterIds.CO2,
}
HERODOT_PRESSURE_PASCALS_PER_HPA = 100


def _sensor_name(observation: dict[str, Any]) -> str | None:
    """Return a known sensor name, including the DS18B20 fallback."""
    sensor = observation.get("sensor")
    if isinstance(sensor, str) and sensor.strip():
        return sensor.strip().casefold()
    model = observation.get("instrumentModel")
    if isinstance(model, str) and model.strip().casefold() == "ds18b20":
        return "temperature"
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO timestamp only when it identifies an aware instant."""
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.utcoffset() is not None else None


def _parse_value(value: Any) -> float | None:
    """Parse a finite numeric value."""
    try:
        parsed = float(value)
    except (ValueError, TypeError, AttributeError):
        return None
    return parsed if math.isfinite(parsed) else None


def _source_identifier(value: Any) -> str | None:
    """Normalize a non-empty source identifier to database text."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    identifier = str(value).strip()
    if not identifier or len(identifier) > 100 or "\x00" in identifier:
        return None
    return identifier


def transform_herodot_observations_with_report(
    raw_json: dict[str, Any],
    source_id: str = "HERODOT",
) -> TransformResult[MeasurementDTO]:
    """Normalize the first-page observation records and report skipped rows."""
    observations = raw_json.get("observations")
    if not isinstance(observations, list):
        raise ValueError("Herodot response must contain an observations list.")

    measurements = []
    skipped: dict[str, int] = {}
    for observation in observations:
        reason: str | None = None
        measurement: MeasurementDTO | None = None
        if not isinstance(observation, dict):
            reason = "invalid_observation"
        else:
            node_id = observation.get("nodeId")
            sensor_name = _sensor_name(observation)
            timestamp = _parse_timestamp(observation.get("timestamp"))
            value = _parse_value(observation.get("value"))
            observation_id = _source_identifier(observation.get("observationId"))
            reading_id = _source_identifier(observation.get("readingId"))

            if not isinstance(node_id, str) or not node_id.strip():
                reason = "missing_node_id"
            elif len(node_id.strip()) > 50 or "\x00" in node_id:
                reason = "invalid_node_id"
            elif (
                observation.get("observationId") is not None and observation_id is None
            ) or (observation.get("readingId") is not None and reading_id is None):
                reason = "invalid_source_identifier"
            elif sensor_name is None:
                reason = "missing_sensor"
            elif sensor_name not in HERODOT_SENSOR_PARAMETERS:
                reason = "unsupported_sensor"
            elif timestamp is None:
                reason = "invalid_timestamp"
            elif value is None:
                reason = "invalid_value"
            else:
                parameter_id = HERODOT_SENSOR_PARAMETERS[sensor_name].value
                if sensor_name == "pressure":
                    value /= HERODOT_PRESSURE_PASCALS_PER_HPA
                measurement = MeasurementDTO(
                    source_id=source_id,
                    station_id=node_id.strip(),
                    parameter_id=parameter_id,
                    timestamp=timestamp,
                    value=value,
                    source_observation_id=observation_id,
                    source_reading_id=reading_id,
                )

        if measurement is not None:
            measurements.append(measurement)
        else:
            if reason is None:
                raise RuntimeError(
                    "Skipped Herodot observation transformation has no reason."
                )
            skipped[reason] = skipped.get(reason, 0) + 1

    return TransformResult(records=measurements, skipped=skipped)


def transform_herodot_observations(
    raw_json: dict[str, Any],
    source_id: str = "HERODOT",
) -> list[MeasurementDTO]:
    """Normalize supported observations from one Herodot response page."""
    return transform_herodot_observations_with_report(raw_json, source_id).records
