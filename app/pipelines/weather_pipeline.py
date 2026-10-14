"""Explicit, composable DMI ETL pipeline."""
from app.transform import DMIDataTransformer
from app.transform_stations import transform_stations


def run_weather_pipeline(source, repository, *, station_source=None, params=None):
    """Run one ingestion cycle; keep extraction, transformation and loading separate."""
    if station_source is not None:
        stations = transform_stations(station_source.fetch())
        repository.save_stations(stations)

    observations = source.fetch(params=params)
    measurements = DMIDataTransformer(source.source_id).transform(observations)
    repository.save_source(source.source_id, source.source_name, "API_DMI")
    repository.save_measurements(measurements)
    return len(measurements)
