"""PostgreSQL connection utilities."""

import os
from typing import Any

import psycopg
from psycopg import Connection


def get_connection() -> Connection[Any]:
    """Create a PostgreSQL connection using the configured environment.

    Returns:
        Active PostgreSQL connection.

    Raises:
        psycopg.Error: If the database connection cannot be established.
    """
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        dbname=os.environ.get("POSTGRES_DB", "postgres_db"),
        user=os.environ.get("POSTGRES_USER", "admin"),
        password=os.environ.get("POSTGRES_PASSWORD", "password"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )


def get_db_connection() -> Connection[Any]:
    """Return an active PostgreSQL connection.

    Returns:
        Active PostgreSQL connection.
    """
    return get_connection()
