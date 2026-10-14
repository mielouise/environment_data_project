"""Concrete ETL pipeline definitions.

This module contains the orchestration logic for the DMI data pipeline.

The pipeline performs the following steps:

1. Fetch station metadata from the DMI Station API.
2. Transform station records into StationDTO objects.
3. Fetch observation data for the configured DMI parameters.
4. Transform observations into MeasurementDTO objects.
5. Persist source metadata, stations, and measurements.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any

from app.database import get_db_connection
from app.extract import SensorDataSource
from app.load import MeasurementRepository
from app.transform import (
    TransformResult,
    transform_dmi_observations_with_report,
    transform_dmi_stations_with_report,
)

DENMARK_BBOX = "7,54,16,58"
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_PAGE_SIZE = 1000
MAX_CONCURRENT_PARAMETER_REQUESTS = 5

EXPECTED_SKIP_REASONS = {
    "superseded_station_version",
}

logger = logging.getLogger(__name__)


def _build_datetime_range(
    lookback_hours: int,
) -> str:
    """Build DMI datetime interval query.

    Creates an ISO 8601 time interval ending at the current
    UTC time and extending backwards by the specified number
    of hours.

    Args:
        lookback_hours:
            Number of hours to look back.

    Returns:
        ISO 8601 datetime interval string.

    Example:
        2026-10-14T10:00:00Z/2026-10-15T10:00:00Z
    """
    now = datetime.now(UTC)

    since = now - timedelta(
        hours=lookback_hours,
    )

    return (
        f"{since.isoformat().replace('+00:00', 'Z')}/"
        f"{now.isoformat().replace('+00:00', 'Z')}"
    )


def _log_transform_result(
    stage: str,
    result: TransformResult[Any],
) -> None:
    """Log transformation statistics.

    Reports:

    - successfully transformed records
    - expected skips
    - unexpected skips

    Args:
        stage:
            Name of the transformation stage.

        result:
            Transformation result object.
    """
    expected_skips = {
        reason: count
        for reason, count in result.skipped.items()
        if reason in EXPECTED_SKIP_REASONS
    }

    unexpected_skips = {
        reason: count
        for reason, count in result.skipped.items()
        if reason not in EXPECTED_SKIP_REASONS
    }

    logger.info(
        "%s transformed %s records.",
        stage,
        len(result.records),
    )

    if expected_skips:
        logger.info(
            "%s expected skips: %s",
            stage,
            expected_skips,
        )

    if unexpected_skips:
        logger.warning(
            "%s unexpected skips: %s",
            stage,
            unexpected_skips,
        )


def _fetch_parameter_observations(
    observation_source: SensorDataSource,
    parameter_id: str,
    datetime_range: str,
) -> list[dict[str, Any]]:
    """Fetch observations for a single DMI parameter.

    Args:
        observation_source:
            Observation data source.

        parameter_id:
            DMI parameter identifier.

        datetime_range:
            ISO 8601 time interval.

    Returns:
        Collection of GeoJSON observation features.
    """
    data = observation_source.fetch(
        params={
            "parameterId": parameter_id,
            "datetime": datetime_range,
            "sortorder": "observed,DESC",
            "bbox": DENMARK_BBOX,
            "limit": DEFAULT_PAGE_SIZE,
        }
    )

    return data.get("features", [])


def run_dmi_pipeline(
    observation_source: SensorDataSource,
    station_source: SensorDataSource,
    parameter_ids: tuple[str, ...],
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> int:
    """Run one complete DMI ETL cycle.

    The pipeline performs extraction, transformation,
    and transactional persistence of station metadata
    and environmental observations.

    Args:
        observation_source:
            DMI observation endpoint source.

        station_source:
            DMI station metadata source.

        parameter_ids:
            DMI parameter identifiers selected for retrieval.

        lookback_hours:
            Number of hours to include in the observation window.

    Returns:
        Number of measurements successfully processed.

    Raises:
        ValueError:
            If invalid parameters are supplied.
    """
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be greater than zero.")

    if not parameter_ids:
        raise ValueError("At least one DMI parameter must be selected.")

    datetime_range = _build_datetime_range(lookback_hours)

    logger.info("Fetching station metadata.")

    station_data = station_source.fetch(
        params={
            "bbox": DENMARK_BBOX,
            "limit": DEFAULT_PAGE_SIZE,
        }
    )

    station_result = transform_dmi_stations_with_report(station_data)

    _log_transform_result(
        "DMI stations",
        station_result,
    )

    fetch_parameter = partial(
        _fetch_parameter_observations,
        observation_source,
        datetime_range=datetime_range,
    )

    logger.info(
        "Fetching observations for %s parameters.",
        len(parameter_ids),
    )

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENT_PARAMETER_REQUESTS,
    ) as executor:
        observation_features = [
            feature
            for features in executor.map(
                fetch_parameter,
                parameter_ids,
            )
            for feature in features
        ]

    logger.info(
        "Fetched %s raw observation features.",
        len(observation_features),
    )

    measurement_result = transform_dmi_observations_with_report(
        {"features": observation_features},
        source_id=observation_source.source_id,
    )

    _log_transform_result(
        "DMI observations",
        measurement_result,
    )

    measurements = measurement_result.records

    logger.info(
        "Prepared %s measurements for persistence.",
        len(measurements),
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

            repository.save_stations(station_result.records)

            repository.save_measurements(measurements)

    finally:
        connection.close()

    logger.info(
        "Successfully persisted %s measurements.",
        len(measurements),
    )

    return len(measurements)
