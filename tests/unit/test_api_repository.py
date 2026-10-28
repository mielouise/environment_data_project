"""Test SQL binding, source isolation, and deterministic page ordering."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.api.models import Measurement, Parameter, Station
from app.api.repository import EnvironmentalReadRepository

type RepositoryFixture = tuple[EnvironmentalReadRepository, MagicMock]

STATION = Station(
    station_id="06180",
    station_name="Copenhagen Airport",
    station_type="Synop",
    country_code="DNK",
    latitude=55.614,
    longitude=12.645,
    station_height=None,
    valid_from=datetime(2026, 1, 1, tzinfo=UTC),
)
MEASUREMENT = Measurement(
    measurement_id=42,
    source_id="DMI",
    source_observation_id=None,
    source_reading_id=None,
    station_id="06180",
    parameter_id=1,
    parameter_name="Temperature",
    unit="°C",
    timestamp=datetime(2026, 10, 26, 10, tzinfo=UTC),
    value=12.3,
)


@pytest.fixture
def repository() -> RepositoryFixture:
    """Provide a repository and its mocked database cursor."""
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    return EnvironmentalReadRepository(connection), cursor


def test_list_measurements_binds_all_filters(
    repository: RepositoryFixture,
) -> None:
    """Bind filter values separately and return typed observations."""
    reader, cursor = repository
    cursor.fetchall.return_value = [MEASUREMENT.model_dump()]
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = datetime(2026, 10, 2, tzinfo=UTC)
    injection = "' OR 1=1 --"
    result = reader.list_measurements(
        source_id="DMI",
        station_id=injection,
        parameter_id=1,
        start=start,
        end=end,
        limit=11,
        offset=20,
    )
    query, values = cursor.execute.call_args.args
    assert injection not in query
    assert values == ["DMI", injection, 1, start, end, 11, 20]
    assert "m.source_id = %s" in query
    assert "m.timestamp >= %s" in query
    assert "m.timestamp <= %s" in query
    assert "ORDER BY m.timestamp DESC, m.measurement_id DESC" in query
    assert result == [MEASUREMENT]


def test_list_measurements_without_filters(
    repository: RepositoryFixture,
) -> None:
    """Retain pagination and source scope without optional filters."""
    reader, cursor = repository
    cursor.fetchall.return_value = []
    reader.list_measurements(
        source_id=None,
        station_id=None,
        parameter_id=None,
        start=None,
        end=None,
        limit=101,
        offset=0,
    )
    query, values = cursor.execute.call_args.args
    assert values == [101, 0]
    assert "m.station_id = %s" not in query
    assert "m.source_id = %s" not in query


def test_station_queries_bind_ids_and_pagination(
    repository: RepositoryFixture,
) -> None:
    """Bind IDs and pagination values and return typed stations."""
    reader, cursor = repository
    cursor.fetchall.return_value = [STATION.model_dump()]
    cursor.fetchone.return_value = STATION.model_dump()
    assert reader.list_stations(11, 20) == [STATION]
    query, values = cursor.execute.call_args.args
    assert "ORDER BY station_id" in query
    assert values == (11, 20)
    assert reader.get_station("06180") == STATION
    assert cursor.execute.call_args.args[1] == ("06180",)
    cursor.fetchone.return_value = None
    assert reader.get_station("unknown") is None


def test_parameter_query_returns_imported_parameters_across_sources(
    repository: RepositoryFixture,
) -> None:
    """Return typed metadata with an optional source filter."""
    reader, cursor = repository
    parameter = Parameter(parameter_id=1, parameter_name="Temperature", unit="°C")
    cursor.fetchall.return_value = [parameter.model_dump()]
    assert reader.list_parameters() == [parameter]
    query = cursor.execute.call_args.args[0]
    assert "EXISTS" in query
    assert "m.source_id" not in query
    reader.list_parameters(source_id="HERODOT")
    query, values = cursor.execute.call_args.args
    assert "m.source_id = %s" in query
    assert values == ("HERODOT",)


def test_get_measurement_is_not_scoped_to_source(
    repository: RepositoryFixture,
) -> None:
    """Return any source's measurement and None for missing IDs."""
    reader, cursor = repository
    cursor.fetchone.return_value = MEASUREMENT.model_dump()
    assert reader.get_measurement(42) == MEASUREMENT
    query, values = cursor.execute.call_args.args
    assert "m.source_id = 'DMI'" not in query
    assert values == (42,)
    cursor.fetchone.return_value = None
    assert reader.get_measurement(999) is None


def test_check_connection(repository: RepositoryFixture) -> None:
    """Use a lightweight query to check database readiness."""
    reader, cursor = repository
    reader.check_connection()
    cursor.execute.assert_called_once_with("SELECT 1")
