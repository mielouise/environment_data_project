"""Test HTTP filtering against PostgreSQL using temporary tables."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app, get_repository
from app.api.repository import EnvironmentalReadRepository
from app.database import get_connection


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide temporary tables and an API client without ETL or DMI.

    Yields:
        A client using an isolated database connection. Closing the
        connection removes the temporary tables after each test.
    """
    # Temporary tables shadow production tables on this connection only.
    # No migrations, production writes, or requests to DMI are needed here.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TEMP TABLE dim_parameters (
                    parameter_id INTEGER, parameter_name TEXT, unit TEXT
                );
                CREATE TEMP TABLE dim_stations (
                    station_id TEXT, station_name TEXT, station_type TEXT,
                    country_code TEXT, latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    station_height DOUBLE PRECISION,
                    valid_from TIMESTAMPTZ
                );
                CREATE TEMP TABLE fact_measurements (
                    measurement_id INTEGER, source_id TEXT,
                    source_observation_id TEXT, source_reading_id TEXT,
                    station_id TEXT, parameter_id INTEGER,
                    timestamp TIMESTAMPTZ, value NUMERIC(10, 2)
                );
                INSERT INTO dim_parameters VALUES
                    (1, 'Temperature', '°C'), (2, 'Humidity', '%'),
                    (4, 'CO2', 'ppm');
                INSERT INTO dim_stations VALUES
                    ('06180', 'Copenhagen Airport', 'Synop', 'DNK',
                     55.614, 12.645, NULL, '2026-01-01T00:00:00Z'),
                    ('06030', 'Aalborg', 'Synop', 'DNK',
                     57.097, 9.85, 3.0, '2026-01-01T00:00:00Z');
                INSERT INTO fact_measurements VALUES
                    (1, 'DMI', NULL, NULL, '06180', 1,
                     '2026-10-26T10:00:00Z', 12.3),
                    (2, 'DMI', NULL, NULL, '06030', 1,
                     '2026-10-26T10:00:00Z', 10.5),
                    (3, 'DMI', NULL, NULL, '06180', 2,
                     '2026-10-26T09:00:00Z', 80.0),
                    (4, 'HERODOT', 'observation-123', 'reading-123',
                     'node-123', 4, '2026-10-26T11:00:00Z', 420.0);
                INSERT INTO dim_stations VALUES
                    ('node-123', NULL, 'sensor_node', NULL,
                     NULL, NULL, NULL, NULL);
                """
            )
        app.dependency_overrides[get_repository] = lambda: EnvironmentalReadRepository(
            connection
        )
        api_client = TestClient(app)
        try:
            # Without the context manager, TestClient does not run the startup
            # migration hook; these tests use only the temporary schema above.
            yield api_client
        finally:
            api_client.close()
            app.dependency_overrides.clear()
            connection.rollback()


def test_postgres_filters_and_inclusive_time_bounds(
    client: TestClient,
) -> None:
    """Match combined filters and include both time bounds."""
    response = client.get(
        "/api/v1/measurements",
        params={
            "station_id": "06180",
            "parameter_id": 1,
            "start": "2026-10-26T11:00:00+01:00",
            "end": "2026-10-26T10:00:00Z",
        },
    )
    assert response.status_code == 200
    rows = response.json()["items"]
    assert len(rows) == 1
    assert rows[0]["measurement_id"] == 1
    assert rows[0]["value"] == 12.3
    assert rows[0]["unit"] == "°C"


def test_postgres_pages_have_stable_order_across_sources(
    client: TestClient,
) -> None:
    """Page through observations from all sources in a stable order."""
    first = client.get("/api/v1/measurements?limit=1").json()
    assert first["items"][0]["measurement_id"] == 4
    assert first["has_more"] is True
    second = client.get("/api/v1/measurements?limit=1&offset=1").json()
    assert second["items"][0]["measurement_id"] == 2
    third = client.get("/api/v1/measurements?limit=1&offset=2").json()
    assert third["items"][0]["measurement_id"] == 1
    last = client.get("/api/v1/measurements?limit=1&offset=3").json()
    assert last["items"][0]["measurement_id"] == 3
    assert last["has_more"] is False
    assert client.get("/api/v1/measurements/4").status_code == 200
    herodot = client.get("/api/v1/measurements?source_id=HERODOT").json()
    assert [row["measurement_id"] for row in herodot["items"]] == [4]
    dmi = client.get("/api/v1/measurements?source_id=DMI&limit=1").json()
    assert dmi["items"][0]["measurement_id"] == 2
    assert dmi["has_more"] is True


def test_postgres_discovery_and_details(client: TestClient) -> None:
    """Discover metadata and retrieve individual stored records."""
    assert client.get("/health").json() == {"status": "ok"}
    assert [p["parameter_id"] for p in client.get("/api/v1/parameters").json()] == [
        1,
        2,
        4,
    ]
    stations = client.get("/api/v1/stations?limit=1").json()
    assert stations["items"][0]["station_id"] == "06030"
    assert stations["has_more"] is True
    assert client.get("/api/v1/stations/06180").json()["station_height"] is None
    herodot_node = client.get("/api/v1/stations/node-123").json()
    assert herodot_node["station_name"] is None
    assert herodot_node["latitude"] is None
    herodot_measurement = client.get("/api/v1/measurements/4").json()
    assert herodot_measurement["value"] == 420.0
    assert herodot_measurement["source_observation_id"] == "observation-123"
    assert herodot_measurement["source_reading_id"] == "reading-123"
    assert client.get("/api/v1/measurements/1").json()["value"] == 12.3
    assert client.get("/api/v1/stations/unknown").status_code == 404


def test_postgres_empty_results_and_sql_binding(client: TestClient) -> None:
    """Treat SQL-like station IDs as ordinary filter values."""
    response = client.get("/api/v1/measurements", params={"station_id": "' OR 1=1 --"})
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["has_more"] is False
    assert client.get("/api/v1/measurements?parameter_id=999").json()["items"] == []


def test_station_migration_allows_unknown_sensor_node_metadata() -> None:
    migration_path = (
        Path(__file__).parents[2]
        / "app"
        / "migrations"
        / "0006_allow_unknown_station_metadata.sql"
    )
    migration_sql = migration_path.read_text(encoding="utf-8")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TEMP TABLE dim_stations (
                    station_id TEXT PRIMARY KEY,
                    station_name TEXT NOT NULL,
                    station_type TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    station_height DOUBLE PRECISION,
                    valid_from TIMESTAMPTZ NOT NULL
                )
                """
            )
            cursor.execute(migration_sql)
            cursor.execute(
                """
                INSERT INTO dim_stations (
                    station_id, station_name, station_type, country_code,
                    latitude, longitude, station_height, valid_from
                )
                VALUES ('node-123', NULL, 'sensor_node', NULL,
                        NULL, NULL, NULL, NULL)
                RETURNING station_id, station_name, country_code, latitude
                """
            )
            assert cursor.fetchone() == ("node-123", None, None, None)


def test_reading_id_migration_preserves_same_timestamp_observations() -> None:
    """Keep distinct source readings and make each ID safe to re-import."""
    migration_path = (
        Path(__file__).parents[2]
        / "app"
        / "migrations"
        / "0007_preserve_source_reading_ids.sql"
    )
    migration_sql = migration_path.read_text(encoding="utf-8")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TEMP TABLE fact_measurements (
                    measurement_id SERIAL PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    station_id TEXT NOT NULL,
                    parameter_id INTEGER NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    value NUMERIC(10, 2) NOT NULL,
                    CONSTRAINT unique_measurement_by_station
                        UNIQUE (source_id, station_id, parameter_id, timestamp)
                )
                """
            )
            cursor.execute(migration_sql)
            for reading_id, value in (("reading-1", 15.0), ("reading-2", 16.0)):
                cursor.execute(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (
                        'HERODOT', 'node-123', 1, '2026-10-28T13:00:00Z',
                        %s, %s, %s
                    )
                    ON CONFLICT (source_id, source_reading_id)
                        WHERE source_reading_id IS NOT NULL
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    (value, f"observation-{reading_id}", reading_id),
                )
            cursor.execute(
                """
                INSERT INTO fact_measurements (
                    source_id, station_id, parameter_id, timestamp, value,
                    source_observation_id, source_reading_id
                )
                VALUES (
                    'HERODOT', 'node-123', 1, '2026-10-28T13:00:00Z',
                    17, 'observation-reading-1', 'reading-1'
                )
                ON CONFLICT (source_id, source_reading_id)
                    WHERE source_reading_id IS NOT NULL
                DO UPDATE SET value = EXCLUDED.value
                """
            )
            for value in (15.0, 16.0):
                cursor.execute(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (
                        'HERODOT', 'node-123', 1, '2026-10-28T13:00:00Z',
                        %s, NULL, NULL
                    )
                    """,
                    (value,),
                )
            cursor.execute(
                """
                SELECT count(*), sum(value)
                FROM fact_measurements
                WHERE source_id = 'HERODOT'
                """
            )
            assert cursor.fetchone() == (4, 64)
            for value in (8.0, 9.0):
                cursor.execute(
                    """
                    INSERT INTO fact_measurements (
                        source_id, station_id, parameter_id, timestamp, value,
                        source_observation_id, source_reading_id
                    )
                    VALUES (
                        'DMI', '06180', 1, '2026-10-28T13:00:00Z',
                        %s, NULL, NULL
                    )
                    ON CONFLICT (source_id, station_id, parameter_id, timestamp)
                        WHERE source_reading_id IS NULL
                            AND source_id <> 'HERODOT'
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    (value,),
                )
            cursor.execute(
                """
                SELECT count(*), sum(value)
                FROM fact_measurements
                WHERE source_id = 'DMI'
                """
            )
            assert cursor.fetchone() == (1, 9)
