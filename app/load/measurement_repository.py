"""PostgreSQL persistence adapter for DMI data."""

from collections.abc import Sequence
from typing import Any

from psycopg import Connection

from app.transform.models import MeasurementDTO, StationDTO


class MeasurementRepository:
    """Persist environmental sources, stations, and measurements."""

    def __init__(self, db_connection: Connection[Any]) -> None:
        """Create a repository using a caller-managed connection."""
        self._connection = db_connection

    def save_source(
        self,
        source_id: str,
        source_name: str,
        source_type: str,
    ) -> None:
        """Upsert descriptive metadata for a data source."""
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO dim_sources (source_id, source_name, source_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE SET
                    source_name = EXCLUDED.source_name,
                    source_type = EXCLUDED.source_type
                """,
                (source_id, source_name, source_type),
            )

    def save_stations(
        self,
        stations: Sequence[StationDTO],
    ) -> None:
        """Upsert station metadata and the latest known location."""
        if not stations:
            return
        rows = [
            (
                station.station_id,
                station.name,
                station.station_type,
                station.country_code,
                station.latitude,
                station.longitude,
                station.station_height,
                station.valid_from,
            )
            for station in stations
        ]
        with self._connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO dim_stations (
                    station_id,
                    name,
                    station_type,
                    country_code,
                    latitude,
                    longitude,
                    station_height,
                    valid_from
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (station_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    station_type = EXCLUDED.station_type,
                    country_code = EXCLUDED.country_code,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    station_height = EXCLUDED.station_height,
                    valid_from = EXCLUDED.valid_from
                WHERE EXCLUDED.valid_from >= dim_stations.valid_from
                """,
                rows,
            )

    def save_measurements(
        self,
        records: Sequence[MeasurementDTO],
    ) -> None:
        """Idempotently insert or update measurements."""
        if not records:
            return
        rows = [
            (
                item.source_id,
                item.station_id,
                item.parameter_id,
                item.timestamp,
                item.value,
            )
            for item in records
        ]
        with self._connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO fact_measurements
                    (source_id, station_id, parameter_id, timestamp, value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT unique_measurement_by_station
                DO UPDATE SET value = EXCLUDED.value
                """,
                rows,
            )
