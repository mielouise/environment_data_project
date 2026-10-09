"""Persistence layer for environmental measurements.

Implements the Repository pattern and encapsulates all database
interaction logic for dimension tables and fact tables.
"""

from app.transform import MeasurementDTO


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
                timestamp,
                value
            )
            VALUES (%s, %s, %s, %s)

            ON CONFLICT (
                source_id,
                parameter_id,
                timestamp
            