"""The concrete DMI pipeline, with explicit stages and dependencies."""
from app.models import StationDTO
from app.transform import transform_observations, transform_stations
from app.transform.dmi import DMI_PARAMETERS

def run_dmi_pipeline(source, repository, *, parameters=DMI_PARAMETERS, filters=None):
    filters = dict(filters or {})
    station_filters = {k: v for k, v in filters.items() if k in ('stationId', 'bbox', 'limit')}
    stations = transform_stations(source.fetch_stations(station_filters), source.source_id)
    measurements = []
    for parameter in parameters:
        payload = source.fetch({**filters, 'parameterId': parameter})
        measurements.extend(transform_observations(payload, source.source_id))
    # Preserve observations even when the station endpoint lacks metadata.
    known = {station.station_id for station in stations}
    for record in measurements:
        if record.station_id is None:
            raise ValueError('DMI observation is missing stationId.')
        if record.station_id not in known:
            stations.append(StationDTO(source.source_id, record.station_id, None, None, None, {}))
            known.add(record.station_id)
    repository.save_source(source.source_id, source.source_name, 'API_DMI')
    repository.save_stations(stations)
    repository.save_measurements(measurements)
    return len(measurements)
