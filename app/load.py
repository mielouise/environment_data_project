"""Module for loading standardized environmental data into PostgreSQL.

Implements the repository architectural pattern to cleanly decouple SQL statements 
and database interaction logic from the core pipeline execution tasks.
"""

from typing import List
from app.transform import MeasurementDTO


class MeasurementRepository:
    """Repository class governing database transactions for weather and sensor entities.

    Encapsulates raw SQL queries to enforce clean schema data updates while isolating 
    underlying connection parameters.
    """

    def __init__(self, db_connection) -> None:
        """Initializes the repository with a live database connection interface.

        Args:
            db_connection: An active psycopg2 database connection instance.
        """
        self._conn = db_connection

    def save_source(self, source_id: str, name: str, source_type: str) -> None:
        """Persists metadata configurations for tracking dynamic measurement origins.

        Ensures cross-referencing capabilities by populating the dimensional
        source tables safely.

        Args:
            source_id: Primary alphanumeric identifier for the origin entity.
            name: Clear descriptive title for documentation lookup.
            source_type: Categorical designation like 'API_DMI' or 'HARDWARE_SENSOR'.
        """
        query = """
            INSERT INTO dim_sources (source_id, source_name, source_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_id) DO NOTHING;
        """
        with self._conn.cursor() as cursor:
            cursor.execute(query, (source_id, name, source_type))
        self._conn.commit()

    def save_measurements(self, records: List[MeasurementDTO]) -> None:
        """Performs batch upsert commands into the core facts measurement database table.

        Leverages psycopg2 executemany for high throughput performance, preventing
        duplicate primary combinations of sources and timestamps.

        Args:
            records: A collection of data objects ready for relational deployment.
        """
        if not records:
            return

        query = """
            INSERT INTO fact_measurements (
                source_id, timestamp, temperature, humidity, co2_ppm, particulate_matter_pm25
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, timestamp) DO UPDATE SET
                temperature = COALESCE(EXCLUDED.temperature, fact_measurements.temperature),
                humidity = COALESCE(EXCLUDED.humidity, fact_measurements.humidity);
        """

        # Convert high-level object attributes into primitive query parameters mapping
        data_to_insert = [
            (
                r.source_id,
                r.timestamp,
                r.temperature,
                r.humidity,
                r.co2_ppm,
                r.particulate_matter_pm25
            )
            for r in records
        ]

        with self._conn.cursor() as cursor:
            cursor.executemany(query, data_to_insert)
        
        self._conn.commit()
