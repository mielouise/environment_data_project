"""Small normalization functions for DMI observations."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any
from app.constants.parameters import ParameterIds


@dataclass(frozen=True)
class MeasurementDTO:
    source_id: str
    parameter_id: int
    timestamp: datetime
    value: float
    station_id: str | None = None


PARAMETER_MAPPING = {
    "temp_dry": ParameterIds.TEMPERATURE,
    "humidity": ParameterIds.HUMIDITY,
    "humidity_past1h": ParameterIds.HUMIDITY_PAST_1H,
    "co2": ParameterIds.CO2,
    "pm25": ParameterIds.PM25,
}


def transform_observation(feature: dict[str, Any], source_id: str) -> MeasurementDTO | None:
    """Transform one observation; return None for malformed or unsupported rows."""
    props = feature.get("properties") or {}
    parameter_id = PARAMETER_MAPPING.get(props.get("parameterId"))
    if parameter_id is None or props.get("observed") is None or props.get("value") is None:
        return None
    try:
        timestamp = datetime.fromisoformat(props["observed"].replace("Z", "+00:00"))
        value = float(props["value"])
        if timestamp.tzinfo is None or not isfinite(value):
            return None
    except (ValueError, TypeError, AttributeError):
        return None
    station = props.get("stationId")
    return MeasurementDTO(
        source_id=source_id, parameter_id=int(parameter_id),
        timestamp=timestamp, value=value,
        station_id=str(station) if station is not None else None,
    )


def transform_measurements(raw_json: dict[str, Any], source_id: str) -> list[MeasurementDTO]:
    """Normalize a collection without coupling parsing to HTTP or persistence."""
    result = []
    for feature in raw_json.get("features", []):
        measurement = transform_observation(feature, source_id)
        if measurement is not None:
            result.append(measurement)
    return result


class DMIDataTransformer:
    """Backward-compatible facade for the existing transform API."""
    PARAMETER_MAPPING = PARAMETER_MAPPING

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id

    def transform(self, raw_json: dict[str, Any]) -> list[MeasurementDTO]:
        return transform_measurements(raw_json, self.source_id)
