-- Preserve historical measurements while adding station-aware identity.
CREATE TABLE IF NOT EXISTS dim_stations (
    station_id VARCHAR(100) PRIMARY KEY,
    station_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

ALTER TABLE fact_measurements
    ADD COLUMN IF NOT EXISTS station_id VARCHAR(100)
        REFERENCES dim_stations(station_id);

-- The original uniqueness constraint merges measurements from distinct stations.
ALTER TABLE fact_measurements DROP CONSTRAINT IF EXISTS unique_measurement;
CREATE UNIQUE INDEX IF NOT EXISTS unique_measurement_with_station
    ON fact_measurements (source_id, parameter_id, timestamp, station_id)
    NULLS NOT DISTINCT;
CREATE INDEX IF NOT EXISTS idx_fact_measurements_station
    ON fact_measurements (station_id);
