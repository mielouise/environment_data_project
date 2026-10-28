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
                    station_name,
                    station_type,
                    country_code,
                    latitude,
                    longitude,
                    station_height,
                    valid_from
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (station_id) DO UPDATE SET
                    station_name = EXCLUDED.station_name,
                    station_type = EXCLUDED.station_type,
                    country_code = EXCLUDED.country_code,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    station_height = EXCLUDED.station_height,
                    valid_from = EXCLUDED.valid_from
                WHERE COALESCE(
                    EXCLUDED.valid_from,
                    '-infinity'::timestamptz
                ) >= COALESCE(
                    dim_stations.valid_from,
                    '-infinity'::timestamptz
                )
                """,
                rows,
            )

    def save_measurements(
        self,
        records: Sequence[MeasurementDTO],
    ) -> None:
        """Persist source-identified readings and upsert legacy measurements.

        Herodot readings with a source reading ID are idempotent by that ID,
        so distinct readings sharing a timestamp are retained. Herodot rows
        without an ID are inserted without conflict resolution rather than
        risking the loss of distinct readings.
        """
        if not records:
            return
        identified_rows = [
            (
                item.source_id,
                item.station_id,
                item.parameter_id,
                item.timestamp,
                item.value,
                item.source_observation_id,
                item.source_reading_id,
            )
            for item in records
            if item.source_reading_id is not None
        ]
        unidentified_herodot_rows = [
            (
                item.source_id,
                item.station_id,
                item.parameter_id,
                item.timestamp,
                item.value,
                item.source_observation_id,
                item.source_reading_id,
            )
            for item in records
            if item.source_id == "HERODOT" and item.source_reading_id is None
        ]
        legacy_rows = [
            (
                item.source_id,
                item.station_id,
                item.parameter_id,
                item.timestamp,
                item.value,
                item.source_observation_id,
                item.source_reading_id,
            )
            for item in records
            if item.source_id != "HERODOT" and item.source_reading_id is None
        ]
        with self._connection.cursor() as cursor:
            if identified_rows:
                cursor.executemany(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, source_reading_id)
                        WHERE source_reading_id IS NOT NULL
                    DO UPDATE SET
                        station_id = EXCLUDED.station_id,
                        parameter_id = EXCLUDED.parameter_id,
                        timestamp = EXCLUDED.timestamp,
                        value = EXCLUDED.value,
                        source_observation_id = EXCLUDED.source_observation_id
                    """,
                    identified_rows,
                )
            if unidentified_herodot_rows:
                cursor.executemany(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    unidentified_herodot_rows,
                )
            if legacy_rows:
                cursor.executemany(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, station_id, parameter_id, timestamp)
                        WHERE source_reading_id IS NULL AND source_id <> 'HERODOT'
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    legacy_rows,
                )
