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
        """Store station IDs plus every dated historical version.

        dim_stations remains a convenient latest-metadata lookup; historical
        geographic joins use dim_station_versions instead.
        """
        if not stations:
            return
        unique_stations: dict[str, StationDTO] = {}
        for station in stations:
            previous = unique_stations.get(station.station_id)
            if previous is None or (
                station.valid_from is not None
                and (previous.valid_from is None or station.valid_from > previous.valid_from)
            ):
                unique_stations[station.station_id] = station

        station_query = """
            INSERT INTO dim_stations (station_id, station_name, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (station_id) DO UPDATE SET
                station_name = EXCLUDED.station_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude;
        """
        versions = [
            (
                station.station_id, station.valid_from, station.valid_to,
                station.station_name, station.latitude, station.longitude,
                station.station_type, station.station_status, station.country,
                station.owner, station.station_height,
            )
            for station in stations
            if station.valid_from is not None
            and (station.valid_to is None or station.valid_to > station.valid_from)
        ]
        version_query = """
            INSERT INTO dim_station_versions (
                station_id, valid_from, valid_to, station_name,
                latitude, longitude, station_type, station_status,
                country, owner, station_height
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (station_id, valid_from) DO UPDATE SET
                valid_to = EXCLUDED.valid_to,
                station_name = EXCLUDED.station_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                station_type = EXCLUDED.station_type,
                station_status = EXCLUDED.station_status,
                country = EXCLUDED.country,
                owner = EXCLUDED.owner,
                station_height = EXCLUDED.station_height;
        """
        with self._conn.cursor() as cursor:
            cursor.executemany(station_query, [
                (station.station_id, station.station_name,
                 station.latitude, station.longitude)
                for station in unique_stations.values()
            ])
            if versions:
                cursor.executemany(version_query, versions)
            # Relink existing measurements when historical metadata arrives later.
            cursor.execute("""
                UPDATE fact_measurements AS f
                SET station_version_id = (
                    SELECT v.station_version_id
                    FROM dim_station_versions v
                    WHERE v.station_id = f.station_id
                      AND v.valid_from <= f.timestamp
                      AND (v.valid_to IS NULL OR f.timestamp < v.valid_to)
                    ORDER BY v.valid_from DESC
                    LIMIT 1
                )
                WHERE f.station_id IS NOT NULL
                  AND EXISTS (
                    SELECT 1 FROM dim_station_versions v
                    WHERE v.station_id = f.station_id
                      AND v.valid_from <= f.timestamp
                      AND (v.valid_to IS NULL OR f.timestamp < v.valid_to)
                  );
            """)
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
        # Enrich new/updated measurements with the station version valid at observation time.
        with self._conn.cursor() as cursor:
            cursor.execute("""
                UPDATE fact_measurements AS f
                SET station_version_id = (
                    SELECT v.station_version_id
                    FROM dim_station_versions v
                    WHERE v.station_id = f.station_id
                      AND v.valid_from <= f.timestamp
                      AND (v.valid_to IS NULL OR f.timestamp < v.valid_to)
                    ORDER BY v.valid_from DESC
                    LIMIT 1
                )
                WHERE f.station_id IS NOT NULL
                  AND f.station_version_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM dim_station_versions v
                    WHERE v.station_id = f.station_id
                      AND v.valid_from <= f.timestamp
                      AND (v.valid_to IS NULL OR f.timestamp < v.valid_to)
                  );
            """)
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
