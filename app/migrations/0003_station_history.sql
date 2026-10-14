-- DMI documents multiple historical metadata versions of a station.
-- Preserve both station identity (dim_stations) and metadata validity periods.
CREATE TABLE IF NOT EXISTS dim_station_versions (
    station_version_id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(100) NOT NULL REFERENCES dim_stations(station_id),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    station_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    station_type TEXT,
    station_status TEXT,
    country TEXT,
    owner TEXT,
    station_height DOUBLE PRECISION,
    CONSTRAINT unique_station_version UNIQUE (station_id, valid_from),
    CONSTRAINT station_valid_interval CHECK (
        valid_to IS NULL OR valid_to > valid_from
    )
);

CREATE INDEX IF NOT EXISTS idx_station_versions_lookup
ON dim_station_versions (station_id, valid_from DESC);

ALTER TABLE fact_measurements
    ADD COLUMN IF NOT EXISTS station_version_id BIGINT
        REFERENCES dim_station_versions(station_version_id);

CREATE INDEX IF NOT EXISTS idx_measurements_station_version
ON fact_measurements (station_version_id);
