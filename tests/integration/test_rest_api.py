"""Test HTTP filtering against PostgreSQL using temporary tables."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.main import app, get_repository
from app.api.repository import DMIReadRepository
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
                    (1, 'DMI', '06180', 1, '2026-10-26T10:00:00Z', 12.3),
                    (2, 'DMI', '06030', 1, '2026-10-26T10:00:00Z', 10.5),
                    (3, 'DMI', '06180', 2, '2026-10-26T09:00:00Z', 80.0),
                    (4, 'OTHER', '06180', 4, '2026-10-26T11:00:00Z', 420.0);
                """
            )
        app.dependency_overrides[get_repository] = lambda: DMIReadRepository(
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


def test_postgres_pages_have_stable_order_and_only_dmi(
    client: TestClient,
) -> None:
    """Page through DMI rows in a stable order."""
    first = client.get("/api/v1/measurements?limit=1").json()
    assert first["items"][0]["measurement_id"] == 2
    assert first["has_more"] is True
    second = client.get("/api/v1/measurements?limit=1&offset=1").json()
    assert second["items"][0]["measurement_id"] == 1
    last = client.get("/api/v1/measurements?limit=1&offset=2").json()
    assert last["items"][0]["measurement_id"] == 3
    assert last["has_more"] is False
    assert client.get("/api/v1/measurements/4").status_code == 404


def test_postgres_discovery_and_details(client: TestClient) -> None:
    """Discover metadata and retrieve individual stored records."""
    assert client.get("/health").json() == {"status": "ok"}
    assert [
        p["parameter_id"] for p in client.get("/api/v1/parameters").json()
    ] == [
        1,
        2,
    ]
    stations = client.get("/api/v1/stations?limit=1").json()
    assert stations["items"][0]["station_id"] == "06030"
    assert stations["has_more"] is True
    assert (
        client.get("/api/v1/stations/06180").json()["station_height"] is None
    )
    assert client.get("/api/v1/measurements/1").json()["value"] == 12.3
    assert client.get("/api/v1/stations/unknown").status_code == 404


def test_postgres_empty_results_and_sql_binding(client: TestClient) -> None:
    """Treat SQL-like station IDs as ordinary filter values."""
    response = client.get(
        "/api/v1/measurements", params={"station_id": "' OR 1=1 --"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["has_more"] is False
    assert (
        client.get("/api/v1/measurements?parameter_id=999").json()["items"]
        == []
    )
