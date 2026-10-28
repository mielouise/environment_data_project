"""Test HTTP contracts, validation, lifecycle, and database failures."""

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.main import app, get_repository

type APIFixture = tuple[TestClient, MagicMock]

STATION = {
    "station_id": "06180",
    "station_name": "Københavns Lufthavn",
    "station_type": "Synop",
    "country_code": "DNK",
    "latitude": 55.614,
    "longitude": 12.645,
    "station_height": None,
    "valid_from": datetime(2026, 1, 1, tzinfo=UTC),
}
MEASUREMENT = {
    "measurement_id": 42,
    "source_id": "DMI",
    "source_observation_id": None,
    "source_reading_id": None,
    "station_id": "06180",
    "parameter_id": 1,
    "parameter_name": "Temperature",
    "unit": "°C",
    "timestamp": datetime(2026, 10, 26, 10, 0, tzinfo=UTC),
    "value": Decimal("12.30"),
}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Generator[APIFixture, None, None]:
    """Provide a client with mocked migrations and repository reads."""
    repository = MagicMock()
    migrations = MagicMock()
    monkeypatch.setattr("app.api.main.apply_migrations", migrations)
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            migrations.assert_called_once_with()
            yield client, repository
    finally:
        app.dependency_overrides.clear()


def test_discovery_and_documentation(api: APIFixture) -> None:
    """Publish the schema, documentation, and parameter units."""
    client, repository = api
    repository.list_parameters.return_value = [
        {"parameter_id": 1, "parameter_name": "Temperature", "unit": "°C"}
    ]
    assert client.get("/", follow_redirects=False).headers["location"] == "/docs"
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/measurements"]["get"]
    assert {p["name"] for p in operation["parameters"]} == {
        "source_id",
        "station_id",
        "parameter_id",
        "start",
        "end",
        "limit",
        "offset",
    }
    assert {"200", "422", "503"} <= operation["responses"].keys()
    response = client.get("/api/v1/parameters")
    assert response.status_code == 200
    assert response.json()[0]["unit"] == "°C"
    repository.list_parameters.assert_called_once_with(source_id=None)
    parameter_operation = schema["paths"]["/api/v1/parameters"]["get"]
    assert {parameter["name"] for parameter in parameter_operation["parameters"]} == {
        "source_id"
    }


def test_health(api: APIFixture) -> None:
    """Check database connectivity before reporting readiness."""
    client, repository = api
    assert client.get("/health").json() == {"status": "ok"}
    repository.check_connection.assert_called_once_with()


def test_station_pages_and_details(api: APIFixture) -> None:
    """Preserve station IDs and nullable metadata in both views."""
    client, repository = api
    repository.list_stations.return_value = [STATION, STATION]
    response = client.get("/api/v1/stations?limit=1&offset=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["station_id"] == "06180"
    assert body["items"][0]["station_height"] is None
    assert (body["limit"], body["offset"], body["has_more"]) == (1, 2, True)
    repository.list_stations.assert_called_once_with(limit=2, offset=2)
    repository.get_station.return_value = STATION
    assert client.get("/api/v1/stations/06180").json()["station_id"] == "06180"
    repository.get_station.assert_called_once_with("06180")


def test_measurement_filters_and_serialization(api: APIFixture) -> None:
    """Forward typed filters and serialize decimals as JSON numbers."""
    client, repository = api
    repository.list_measurements.return_value = [MEASUREMENT]
    response = client.get(
        "/api/v1/measurements",
        params={
            "station_id": "06180",
            "parameter_id": 1,
            "start": "2026-10-26T10:00:00Z",
            "end": "2026-10-26T11:00:00Z",
            "limit": 1,
            "offset": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["value"] == 12.3
    assert body["items"][0]["timestamp"] == "2026-10-26T10:00:00Z"
    assert body["has_more"] is False
    repository.list_measurements.assert_called_once_with(
        source_id=None,
        station_id="06180",
        parameter_id=1,
        start=datetime(2026, 10, 26, 10, tzinfo=UTC),
        end=datetime(2026, 10, 26, 11, tzinfo=UTC),
        limit=2,
        offset=3,
    )
    repository.get_measurement.return_value = MEASUREMENT
    assert client.get("/api/v1/measurements/42").json()["measurement_id"] == 42
    repository.get_measurement.assert_called_once_with(42)


def test_measurement_source_filter(api: APIFixture) -> None:
    client, repository = api
    repository.list_measurements.return_value = []

    response = client.get("/api/v1/measurements?source_id=HERODOT")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert repository.list_measurements.call_args.kwargs["source_id"] == "HERODOT"


@pytest.mark.parametrize("resource", ["measurements", "stations"])
def test_empty_pages(api: APIFixture, resource: str) -> None:
    """Return an exhausted page for an empty search."""
    client, repository = api
    getattr(repository, f"list_{resource}").return_value = []
    response = client.get(f"/api/v1/{resource}")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "limit": 100,
        "offset": 0,
        "has_more": False,
    }


@pytest.mark.parametrize(
    ("resource", "identifier", "method"),
    [
        ("stations", "unknown", "get_station"),
        ("measurements", "999", "get_measurement"),
    ],
)
def test_missing_resources(
    api: APIFixture, resource: str, identifier: str, method: str
) -> None:
    """Translate missing resource IDs to HTTP 404 responses."""
    client, repository = api
    getattr(repository, method).return_value = None
    response = client.get(f"/api/v1/{resource}/{identifier}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=1001",
        "limit=abc",
        "offset=-1",
        "parameter_id=0",
        "parameter_id=temp_dry",
        "start=invalid",
        "start=2026-10-26T10:00:00",
        "start=2026-10-27T00:00:00Z&end=2026-10-26T00:00:00Z",
        "station_id=",
        "station_id=" + "a" * 51,
    ],
)
def test_invalid_queries(api: APIFixture, query: str) -> None:
    """Reject invalid filters before executing a measurement query."""
    client, repository = api
    assert client.get(f"/api/v1/measurements?{query}").status_code == 422
    repository.list_measurements.assert_not_called()


@pytest.mark.parametrize("path", ["stations?limit=1001", "measurements/0"])
def test_other_invalid_inputs(api: APIFixture, path: str) -> None:
    """Check numeric bounds on station pages and measurement paths."""
    client, _ = api
    assert client.get(f"/api/v1/{path}").status_code == 422


def test_timezones_and_equal_time_bounds(api: APIFixture) -> None:
    """Accept equal instants with different timezone offsets."""
    client, repository = api
    repository.list_measurements.return_value = []
    response = client.get(
        "/api/v1/measurements",
        params={
            "start": "2026-10-26T11:00:00+01:00",
            "end": "2026-10-26T10:00:00Z",
        },
    )
    assert response.status_code == 200


def test_database_error_does_not_expose_connection_details(
    api: APIFixture,
) -> None:
    """Return a generic HTTP 503 when querying fails."""
    client, repository = api
    repository.check_connection.side_effect = psycopg.OperationalError(
        "secret password"
    )
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database unavailable. Please try again later."
    }


def test_read_only_connection_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use read-only transactions and close request connections."""
    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr("app.api.main.get_connection", connect)
    dependency = get_repository()
    assert next(dependency)._connection is connection
    assert connection.read_only is True
    dependency.close()
    connect.return_value.__exit__.assert_called_once()


def test_connection_failure_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hide private database settings when connecting fails."""
    connect = MagicMock(
        side_effect=psycopg.OperationalError("private connection details")
    )
    monkeypatch.setattr("app.api.main.get_connection", connect)
    monkeypatch.setattr("app.api.main.apply_migrations", MagicMock())
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert "private" not in response.text
