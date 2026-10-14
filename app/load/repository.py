"""Persistence layer for environmental measurements.

Implements the Repository pattern and encapsulates all database
interaction logic for dimension tables and fact tables.
"""

from app.models import MeasurementDTO, StationDTO
from psycopg.types.json import Jsonb


class MeasurementRepository:
    """Repository responsible for persisting environmental data."""

    def __init__(
        self,
        db_connection
    ) -> None:
        """Initialize repository.

        Args:
            db_connection:
                Active PostgreSQL connection instance.
        """
        self._conn = db_connection

    def save_source(
        self,
        source_id: str,
        source_name: str,
        source_type: str
    ) -> None:
        """Persist source metadata into dim_sources.

        Args:
            source_id:
                Unique source identifier.

            source_name:
                Human-readable source name.

            source_type:
                Classification of the source.
        """

        query = """
            INSERT INTO dim_sources (
                source_id,
                source_name,
                source_type
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (source_id)
            DO NOTHING;
        """

        with self._conn.cursor() as cursor:
            cursor.execute(
                query,
                (
                    source_id,
                    source_name,
                    source_type,
                ),
            )

        self._conn.commit()

    def save_measurements(
        self,
        records: list[MeasurementDTO]
    ) -> None:
        """Persist measurements into fact_measurements.

        Existing measurements are updated when a matching
        source, parameter and timestamp combination already
        exists.

        Args:
            records:
                Collection of MeasurementDTO objects.
        """

        if not records:
            return

        query = """
            INSERT INTO fact_measurements (
                source_id,
                parameter_id,
                station_id,
                timestamp,
                value
            )
            VALUES (%s, %s, %s, %s, %s)

            ON CONFLICT (
                source_id,
                parameter_id,
                station_id,
                timestamp
            )
            DO UPDATE SET
                value = EXCLUDED.value;
        """

        measurement_rows = [
            (
                record.source_id,
                record.parameter_id,
                record.station_id,
                record.timestamp,
                record.value,
            )
            for record in records
        ]

        with self._conn.cursor() as cursor:
            cursor.executemany(
                query,
                measurement_rows,
            )

        self._conn.commit()

    def save_stations(self, records: list[StationDTO]) -> None:
        if not records:
            return
        with self._conn.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO dim_stations (source_id, station_id, name, longitude, latitude, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id, station_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, dim_stations.name),
                    longitude = COALESCE(EXCLUDED.longitude, dim_stations.longitude),
                    latitude = COALESCE(EXCLUDED.latitude, dim_stations.latitude),
                    metadata = dim_stations.metadata || EXCLUDED.metadata;
            """, [(r.source_id, r.station_id, r.name, r.longitude, r.latitude, Jsonb(r.metadata))
                  for r in records])
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""

        if self._conn is not None:
            self._conn.close()