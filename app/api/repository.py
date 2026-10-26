"""Read-only, parameterized PostgreSQL queries for the public API."""

from datetime import datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from app.api.models import Measurement, Parameter, Station

MEASUREMENT_COLUMNS = """
    m.measurement_id, m.source_id, m.station_id, m.parameter_id,
    p.parameter_name, p.unit, m.timestamp, m.value
"""
STATION_COLUMNS = """
    station_id, station_name, station_type, country_code,
    latitude, longitude, station_height, valid_from
"""


class DMIReadRepository:
    """Read imported DMI data using a caller-managed connection."""

    def __init__(self, connection: Connection[Any]) -> None:
        """Use a connection whose lifetime is managed by the caller.

        Args:
            connection: PostgreSQL connection supplied by the API.
        """
        self._connection = connection

    def check_connection(self) -> None:
        """Verify connectivity with a lightweight query.

        Raises:
            psycopg.Error: If PostgreSQL cannot execute the query.
        """
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    def list_parameters(self) -> list[Parameter]:
        """Return parameter metadata for stored DMI observations.

        Returns:
            Parameters ordered by database ID, excluding types without
            imported DMI measurements.
        """
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT p.parameter_id, p.parameter_name, p.unit
                FROM dim_parameters p
                WHERE EXISTS (
                    SELECT 1 FROM fact_measurements m
                    WHERE m.parameter_id = p.parameter_id
                        AND m.source_id = 'DMI'
                )
                ORDER BY p.parameter_id
                """
            )
            return [Parameter.model_validate(row) for row in cursor.fetchall()]

    def list_stations(self, limit: int, offset: int) -> list[Station]:
        """Return a bounded slice of imported station metadata.

        Args:
            limit: Maximum rows, including pagination lookahead.
            offset: Number of station rows to skip.

        Returns:
            Stations ordered by their string IDs with leading zeros.
        """
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT {STATION_COLUMNS} FROM dim_stations
                ORDER BY station_id LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            return [Station.model_validate(row) for row in cursor.fetchall()]

    def get_station(self, station_id: str) -> Station | None:
        """Return station metadata, or None when the station is unknown.

        Args:
            station_id: DMI station ID, including leading zeros.
        """
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT {STATION_COLUMNS} FROM dim_stations
                WHERE station_id = %s
                """,
                (station_id,),
            )
            row = cursor.fetchone()
            return Station.model_validate(row) if row is not None else None

    def list_measurements(
        self,
        *,
        station_id: str | None,
        parameter_id: int | None,
        start: datetime | None,
        end: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Measurement]:
        """Return DMI observations matching every supplied filter.

        Args:
            station_id: Station ID, or None for all stations.
            parameter_id: Database parameter ID, or None for all types.
            start: Inclusive earliest time, or None for no bound.
            end: Inclusive latest time, or None for no bound.
            limit: Maximum rows, including pagination lookahead.
            offset: Number of matching observations to skip.

        Returns:
            Measurements ordered by descending timestamp and ID.
            Every filter value is bound as a separate SQL parameter.
        """
        conditions = ["m.source_id = 'DMI'"]
        values: list[str | int | datetime] = []
        # Keep SQL clauses fixed and bind client values separately.
        for clause, value in (
            ("m.station_id = %s", station_id),
            ("m.parameter_id = %s", parameter_id),
            ("m.timestamp >= %s", start),
            ("m.timestamp <= %s", end),
        ):
            if value is not None:
                conditions.append(clause)
                values.append(value)
        values.extend((limit, offset))
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT {MEASUREMENT_COLUMNS}
                FROM fact_measurements m
                JOIN dim_parameters p ON p.parameter_id = m.parameter_id
                WHERE {" AND ".join(conditions)}
                ORDER BY m.timestamp DESC, m.measurement_id DESC
                LIMIT %s OFFSET %s
                """,
                values,
            )
            return [
                Measurement.model_validate(row) for row in cursor.fetchall()
            ]

    def get_measurement(self, measurement_id: int) -> Measurement | None:
        """Return a DMI observation, or None for missing or non-DMI IDs.

        Args:
            measurement_id: Database primary key of the observation.
        """
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT {MEASUREMENT_COLUMNS}
                FROM fact_measurements m
                JOIN dim_parameters p ON p.parameter_id = m.parameter_id
                WHERE m.source_id = 'DMI' AND m.measurement_id = %s
                """,
                (measurement_id,),
            )
            row = cursor.fetchone()
            return Measurement.model_validate(row) if row is not None else None
