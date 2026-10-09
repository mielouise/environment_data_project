"""Database connection and schema initialization utilities.

This module is responsible for:

- Establishing PostgreSQL connections.
- Initializing the database schema.
- Seeding dimension tables with default values.
"""

import os
import sys
from typing import Any

import psycopg


def get_connection() -> Any:
    """Create and return a PostgreSQL database connection.

    Returns:
        Active PostgreSQL connection.

    Raises:
        Exception:
            Raised if connection establishment fails.
    """
    try:
        return psycopg.connect(
            host=os.environ.get(
                "POSTGRES_HOST",
                "db"
            ),
            dbname=os.environ.get(
                "POSTGRES_DB",
                "postgres_db"
            ),
            user=os.environ.get(
                "POSTGRES_USER",
                "admin"
            ),
            password=os.environ.get(
                "POSTGRES_PASSWORD",
                "password"
            ),
            port=os.environ.get(
                "POSTGRES_PORT",
                "5432"
            )
        )

    except Exception as err:
        print(
            f"Database connection establishment failed: {err}",
            file=sys.stderr
        )
        raise


def get_db_connection() -> Any:
    """Return an active PostgreSQL connection.

    Returns:
        Active PostgreSQL connection.
    """
    return get_connection()


def create_tables() -> None:
    """Initialize database schema.

    Creates all dimension and fact tables required by the
    environmental ETL pipeline and seeds the parameter dimension.
    """

    commands = (
        """
        CREATE TABLE IF NOT EXISTS dim_sources (
            source_id VARCHAR(50) PRIMARY KEY,
            source_name VARCHAR(100) NOT NULL,
            source_type VARCHAR(50) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_parameters (
            parameter_id INTEGER PRIMARY KEY,
            parameter_name VARCHAR(100) NOT NULL UNIQUE,
            unit VARCHAR(20) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_measurements (
            measurement_id SERIAL PRIMARY KEY,

            source_id VARCHAR(50) NOT NULL
                REFERENCES dim_sources(source_id),

            parameter_id INTEGER NOT NULL
                REFERENCES dim_parameters(parameter_id),

            timestamp TIMESTAMPTZ NOT NULL,

            value NUMERIC(10, 2) NOT NULL,

            CONSTRAINT unique_measurement
                UNIQUE (
                    source_id,
                    parameter_id,
                    timestamp
                )
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fact_measurements_timestamp
        ON fact_measurements (timestamp);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fact_measurements_source
        ON fact_measurements (source_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fact_measurements_parameter
        ON fact_measurements (parameter_id);
        """
    )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            for command in commands:
                cursor.execute(command)

            cursor.execute(
                """
                INSERT INTO dim_parameters (
                    parameter_id,
                    parameter_name,
                    unit
                )
                VALUES
                    (1, 'Temperature', '°C'),
                    (2, 'Humidity', '%'),
                    (3, 'Humidity Past 1 Hour', '%'),
                    (4, 'CO2', 'ppm'),
                    (5, 'PM2.5', 'μg/m³')
                ON CONFLICT (parameter_id)
                DO NOTHING;
                """
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()