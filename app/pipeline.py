"""Concrete ETL pipeline definitions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from app.database import get_db_connection
from app.extract import SensorDataSource
from app.load import MeasurementRepository
from app.transform import (
    transform_dmi_observations,
    transform_dmi_stations,
)

DENMARK_BBOX = "7,54,16,58"
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_PAGE_SIZE = 1000
MAX_CONCURRENT_PARAMETER_REQUESTS = 5


def _fetch_parameter_observations(
    observation_source: SensorDataSource,
    parameter_id: str,
    datetime_range: str,
) -> list[dict[str, Any]]:
    """Fetch one parameter's observations for the requested time window."""
    data = observation_source.fetch(
        params={
            "parameterId": parameter_id,
            "datetime": datetime_range,
            "sortorder": "observed,DESC",
            "bbox": DENMARK_BBOX,
            "limit": DEFAULT_PAGE_SIZE,
        }
    )
    return data["features"]


def run_dmi_pipeline(
    observation_source: SensorDataSource,
    station_source: SensorDataSource,
    parameter_ids: tuple[str, ...],
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> int:
    """Extract, transform, and transactionally load one DMI data cycle.

    Args:
        observation_source:
            DMI meteorological observation endpoint.

        station_source:
            DMI station metadata endpoint.

        parameter_ids:
            DMI parameter identifiers selected for collection.

        lookback_hours:
            Rolling observation window ending at the current UTC time.

    Returns:
        Number of processed measurements.
    """
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be greater than zero.")
    if not parameter_ids:
        raise ValueError("At least one DMI parameter must be selected.")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=lookback_hours)
    datetime_range = (
        f"{since.isoformat().replace('+00:00', 'Z')}/"
        f"{now.isoformat().replace('+00:00', 'Z')}"
    )
    station_data = station_source.fetch(
        params={
            "bbox": DENMARK_BBOX,
            "limit": DEFAULT_PAGE_SIZE,
        }
    )
    stations = transform_dmi_stations(station_data)

    fetch_parameter = partial(
        _fetch_parameter_observations,
        observation_source,
        datetime_range=datetime_range,
    )
    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENT_PARAMETER_REQUESTS
    ) as executor:
        observation_features = [
            feature
            for features in executor.map(fetch_parameter, parameter_ids)
            for feature in features
        ]

    measurements = transform_dmi_observations(
        {"features": observation_features},
        source_id=observation_source.source_id,
    )

    connection = get_db_connection()
    try:
        with connection.transaction():
            repository = MeasurementRepository(connection)
            repository.save_source(
                source_id=observation_source.source_id,
                source_name=observation_source.source_name,
                source_type="API_DMI",
            )
            repository.save_stations(stations)
            repository.save_measurements(measurements)
    finally:
        connection.close()

    return len(measurements)