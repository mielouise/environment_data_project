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
    """Initializes the database schema by building the required dimensional fact tables."""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS dim_sources (
            source_id VARCHAR(50) PRIMARY KEY,
            source_name VARCHAR(100) NOT NULL,
            source_type VARCHAR(50) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_measurements (
            measurement_id SERIAL PRIMARY KEY,
            source_id VARCHAR(50) REFERENCES dim_sources(source_id),
            timestamp TIMESTAMPTZ NOT NULL,
            temperature NUMERIC(5, 2),
            humidity NUMERIC(5, 2),
            co2_ppm INT,
            particulate_matter_pm25 NUMERIC(6, 2),
            CONSTRAINT unique_source_timestamp UNIQUE (source_id, timestamp)
        );
        """
    )
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for command in commands:
                cursor.execute(command)
        conn.commit()
    finally:
        conn.close()
