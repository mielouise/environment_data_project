CREATE TABLE dim_stations (
    source_id VARCHAR(50) NOT NULL REFERENCES dim_sources(source_id),
    station_id VARCHAR(50) NOT NULL,
    name TEXT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_id, station_id)
);
ALTER TABLE fact_measurements ADD COLUMN station_id VARCHAR(50);
ALTER TABLE fact_measurements DROP CONSTRAINT unique_measurement;
ALTER TABLE fact_measurements ADD CONSTRAINT unique_measurement
    UNIQUE NULLS NOT DISTINCT (source_id, station_id, parameter_id, timestamp);
ALTER TABLE fact_measurements ADD CONSTRAINT measurement_station
    FOREIGN KEY (source_id, station_id) REFERENCES dim_stations(source_id, station_id);
CREATE INDEX idx_fact_measurements_station ON fact_measurements (source_id, station_id);
