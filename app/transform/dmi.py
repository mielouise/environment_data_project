"""Pure, independently testable DMI transformations."""
from datetime import datetime
import math
from app.constants.parameters import ParameterIds
from app.models import MeasurementDTO, StationDTO

PARAMETER_MAPPING = {
    "temp_dry": ParameterIds.TEMPERATURE,
    "humidity": ParameterIds.HUMIDITY,
    "humidity_past1h": ParameterIds.HUMIDITY_PAST_1H,
    "co2": ParameterIds.CO2,
    "pm25": ParameterIds.PM25,
}
# CO2/PM2.5 remain internal dimensions for future air-quality sources.
DMI_PARAMETERS = ("temp_dry", "humidity", "humidity_past1h")

def transform_observation(feature, source_id="DMI"):
    properties = feature.get("properties") or {}
    parameter_id = PARAMETER_MAPPING.get(properties.get("parameterId"))
    if parameter_id is None:
        return None
    try:
        timestamp = datetime.fromisoformat(properties["observed"].replace("Z", "+00:00"))
        value = float(properties["value"])
        if timestamp.tzinfo is None or not math.isfinite(value):
            return None
        station_id = properties.get("stationId")
        if station_id is not None and (not isinstance(station_id, str) or not station_id):
            return None
        return MeasurementDTO(source_id, parameter_id.value, timestamp, value, station_id)
    except (KeyError, ValueError, TypeError, AttributeError):
        return None

def transform_observations(payload, source_id="DMI"):
    return [record for feature in payload.get("features", [])
            if (record := transform_observation(feature, source_id)) is not None]

def transform_station(feature, source_id="DMI"):
    properties = feature.get("properties") or {}
    station_id = properties.get("stationId")
    if not isinstance(station_id, str) or not station_id:
        return None
    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    longitude = latitude = None
    if len(coordinates) >= 2:
        try:
            longitude, latitude = map(float, coordinates[:2])
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                longitude = latitude = None
        except (ValueError, TypeError):
            pass
    return StationDTO(source_id, station_id, properties.get("name"), longitude, latitude, properties)

def transform_stations(payload, source_id="DMI"):
    # A station may have multiple historical metadata versions. Keep the latest.
    stations = {}
    for feature in sorted(payload.get("features", []),
                          key=lambda f: str((f.get("properties") or {}).get("validFrom") or "")):
        record = transform_station(feature, source_id)
        if record is not None:
            stations[record.station_id] = record
    return list(stations.values())
