"""PostgreSQL connection management."""
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
