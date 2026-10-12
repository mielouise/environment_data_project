"""Database connection and schema initialization utilities.

This module is responsible for:

- Establishing PostgreSQL connections.
- Initializing the database schema.
- Seeding dimension tables with default values.
"""

import os
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(?P<version>\d+)_(?P<name>[a-z0-9_]+)\.sql$"
)


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
    """Apply pending database migrations.

    Migration versions and checksums are stored in ``schema_migrations``.
    Existing databases are upgraded in place by the initial idempotent
    migration.
    """

    migrations = []
    for migration_path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_FILENAME_PATTERN.fullmatch(
            migration_path.name
        )
        if match is None:
            raise ValueError(
                "Invalid migration filename "
                f"{migration_path.name!r}; expected "
                "<version>_<name>.sql."
            )

        migration_sql = migration_path.read_text(encoding="utf-8")
        migrations.append(
            (
                int(match.group("version")),
                match.group("name"),
                migration_sql,
                sha256(migration_sql.encode("utf-8")).hexdigest(),
            )
        )

    migrations.sort(key=lambda migration: migration[0])
    versions = [migration[0] for migration in migrations]
    if len(versions) != len(set(versions)):
        raise ValueError("Database migration versions must be unique.")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_advisory_xact_lock(829271, 1);
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    checksum CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                SELECT version, name, checksum
                FROM schema_migrations;
                """
            )
            applied_migrations = {
                version: (name, checksum.strip())
                for version, name, checksum in cursor.fetchall()
            }
            available_migrations = {
                version: (name, migration_checksum, migration_sql)
                for version, name, migration_sql, migration_checksum
                in migrations
            }

            for version, (name, checksum) in applied_migrations.items():
                migration = available_migrations.get(version)
                if migration is None:
                    raise RuntimeError(
                        f"Applied database migration {version} is "
                        "missing from the migrations directory."
                    )
                if migration[:2] != (name, checksum):
                    raise RuntimeError(
                        f"Applied database migration {version} has "
                        "changed; committed migrations must remain "
                        "immutable."
                    )

            for version, name, migration_sql, checksum in migrations:
                if version in applied_migrations:
                    continue

                cursor.execute(migration_sql)
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (
                        version,
                        name,
                        checksum
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (version, name, checksum),
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()