"""Database persistence for observations, sources and stations."""
from app.transform.observations import MeasurementDTO
from app.transform.stations import StationDTO


class MeasurementRepository:
    def __init__(self, db_connection):
        self._conn = db_connection

    def save_source(self, source_id: str, source_name: str, source_type: str) -> None:
        query = """
            INSERT INTO dim_sources (source_id, source_name, source_type)
            VALUES (%s, %s, %s) ON CONFLICT (source_id)
            DO UPDATE SET source_name = EXCLUDED.source_name,
                          source_type = EXCLUDED.source_type;
        """
        with self._conn.cursor() as cursor:
            cursor.execute(query, (source_id, source_name, source_type))
        self._conn.commit()

    def save_stations(self, stations: list[StationDTO]) -> None:
        if not stations:
            return
        query = """
            INSERT INTO dim_stations (station_id, station_name, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (station_id) DO UPDATE SET
                station_name = EXCLUDED.station_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude;
        """
        with self._conn.cursor() as cursor:
            cursor.executemany(query, [
                (s.station_id, s.station_name, s.latitude, s.longitude) for s in stations
            ])
        self._conn.commit()

    def save_measurements(self, records: list[MeasurementDTO]) -> None:
        if not records:
            return
        query = """
            INSERT INTO fact_measurements (
                source_id, parameter_id, timestamp, value, station_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_id, parameter_id, timestamp, station_id)
            DO UPDATE SET value = EXCLUDED.value;
        """
        with self._conn.cursor() as cursor:
            # Some observations refer to stations absent from the station endpoint
            # (for example historic or inactive stations). Preserve their identity.
            missing_station_ids = sorted({
                record.station_id for record in records
                if record.station_id is not None
            })
            if missing_station_ids:
                cursor.executemany(
                    """
                    INSERT INTO dim_stations (station_id)
                    VALUES (%s)
                    ON CONFLICT (station_id) DO NOTHING;
                    """,
                    [(station_id,) for station_id in missing_station_ids],
                )
            cursor.executemany(query, [
                (r.source_id, r.parameter_id, r.timestamp, r.value, r.station_id)
                for r in records
            ])
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
