"""Database connection utilities; SQL migrations live in migration_runner.py."""
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

from app.migration_runner import apply_migrations

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_connection() -> Any:
    """Create a PostgreSQL connection configured through environment variables."""
    try:
        return psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "db"),
            dbname=os.environ.get("POSTGRES_DB", "postgres_db"),
            user=os.environ.get("POSTGRES_USER", "admin"),
            password=os.environ.get("POSTGRES_PASSWORD", "password"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
        )
    except Exception as err:
        print(f"Database connection establishment failed: {err}", file=sys.stderr)
        raise


def get_db_connection() -> Any:
    return get_connection()


def create_tables() -> None:
    """Apply immutable migrations using the configured database connection."""
    apply_migrations(get_connection, MIGRATIONS_DIR)
