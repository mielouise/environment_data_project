"""Module managing the PostgreSQL database connection and schema initialization."""

import os
import sys
from typing import Any
import psycopg


def get_connection() -> Any:
    """Creates and returns a connection instance to the PostgreSQL container database.

    Aligned to match the project's pre-configured integration tests.

    Returns:
        A live connection object mapping to the environment variables specifications.
    """
    try:
        return psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "db"),
            dbname=os.environ.get("POSTGRES_DB", "postgres_db"),
            user=os.environ.get("POSTGRES_USER", "admin"),
            password=os.environ.get("POSTGRES_PASSWORD", "password"),
            port=os.environ.get("POSTGRES_PORT", "5432")
        )
    except Exception as err:
        print(f"Database connection establishment failed: {err}", file=sys.stderr)
        raise


def get_db_connection() -> Any:
    """Alias pointing to get_connection to support internal ETL pipeline components.

    Returns:
        An active database connection object.
    """
    return get_connection()


def create_tables() -> None:
    """Initialize the database schema."""

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
            parameter_id SERIAL PRIMARY KEY,
            parameter_name VARCHAR(50) NOT NULL UNIQUE,
            unit VARCHAR(20) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_measurements (
            measurement_id SERIAL PRIMARY KEY,
            source_id VARCHAR(50)
                REFERENCES dim_sources(source_id),

            parameter_id INTEGER
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
        """
    )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            for command in commands:
                cursor.execute(command)

            cursor.execute(
                """
                INSERT INTO dim_parameters
                    (parameter_name, unit)
                VALUES
                    ('Temperature', '°C'),
                    ('Humidity', '%'),
                    ('CO2', 'ppm'),
                    ('PM2.5', 'μg/m³')
                ON CONFLICT (parameter_name)
                DO NOTHING;
                """
            )

        conn.commit()

    finally:
        conn.close()