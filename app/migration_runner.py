"""Database migration discovery and execution."""

import re
from hashlib import sha256
from pathlib import Path

from app.database import get_connection

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_FILENAME_PATTERN = re.compile(r"^(?P<version>\d+)_(?P<name>[a-z0-9_]+)\.sql$")


def apply_migrations() -> None:
    """Apply pending database migrations in version order."""
    migrations = []
    for migration_path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_FILENAME_PATTERN.fullmatch(migration_path.name)
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
            cursor.execute("SELECT pg_advisory_xact_lock(829271, 1);")
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
                for version, name, migration_sql, migration_checksum in migrations
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
