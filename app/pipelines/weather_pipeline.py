"""Concrete pipeline comprising multiple DMI requests and two destination tables."""
from app.transform.observations import transform_measurements
from app.transform.stations import transform_stations


def run_weather_pipeline(source, repository, *, station_source=None, params=None):
    """Run stations first, then one observation request per selected parameter.

    This function intentionally depends only on small fetch/transform/save steps.
    """
    if station_source is not None:
        repository.save_stations(transform_stations(station_source.fetch()))

    requested = dict(params or {})
    selected = requested.pop("parameterIds", None)
    if selected is None:
        selected = [requested.pop("parameterId")] if "parameterId" in requested else [None]

    measurements = []
    for parameter in selected:
        query = dict(requested)
        if parameter is not None:
            query["parameterId"] = parameter
        payload = source.fetch(params=query)
        measurements.extend(transform_measurements(payload, source.source_id))

    repository.save_source(source.source_id, source.source_name, "API_DMI")
    repository.save_measurements(measurements)
    return len(measurements)
