"""Database checks against the disposable PostgreSQL service in CI."""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest

from app.database import get_connection
from app.load.measurement_repository import MeasurementRepository
from app.migration_runner import MIGRATIONS_DIR, apply_migrations
from app.transform.models import MeasurementDTO, StationDTO


def test_database_connection():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        assert result[0] == 1

    finally:
        connection.close()


def test_migrations_and_repository_round_trip():
    """Apply real SQL twice and verify idempotent writes and FK constraints."""
    apply_migrations()
    apply_migrations()

    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM schema_migrations")
                assert cursor.fetchone()[0] == len(list(MIGRATIONS_DIR.glob("*.sql")))

            repository = MeasurementRepository(connection)
            repository.save_source("CI_TEST", "CI test source", "test")
            observed_at = datetime(2026, 1, 1, tzinfo=UTC)
            repository.save_stations(
                [
                    StationDTO(
                        station_id="CI_TEST",
                        name="CI test station",
                        station_type="Synop",
                        country_code="DNK",
                        latitude=55.67,
                        longitude=12.57,
                        station_height=None,
                        valid_from=observed_at,
                    )
                ]
            )
            measurement = MeasurementDTO(
                source_id="CI_TEST",
                station_id="CI_TEST",
                parameter_id=1,
                timestamp=observed_at,
                value=12.34,
            )
            repository.save_measurements([measurement])
            repository.save_measurements([measurement])
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT value FROM fact_measurements WHERE source_id = %s",
                    ("CI_TEST",),
                )
                assert cursor.fetchall() == [(Decimal("12.34"),)]

            with (
                pytest.raises(psycopg.errors.ForeignKeyViolation),
                connection.transaction(),
            ):
                repository.save_measurements(
                    [
                        MeasurementDTO(
                            source_id="CI_TEST",
                            station_id="CI_MISSING_STATION",
                            parameter_id=1,
                            timestamp=observed_at,
                            value=1,
                        )
                    ]
                )
        finally:
            # Keep local development data intact when running the suite manually.
            connection.rollback()
