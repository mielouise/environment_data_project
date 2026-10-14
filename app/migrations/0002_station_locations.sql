CREATE TABLE dim_stations (
    station_id VARCHAR(50) PRIMARY KEY,
    station_name VARCHAR(100) NOT NULL,
    station_type VARCHAR(50) NOT NULL,
    country_code VARCHAR(3) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    station_height DOUBLE PRECISION,
    valid_from TIMESTAMPTZ NOT NULL
);

ALTER TABLE fact_measurements
    ADD COLUMN station_id VARCHAR(50)
        REFERENCES dim_stations(station_id);

ALTER TABLE fact_measurements
    DROP CONSTRAINT unique_measurement;

ALTER TABLE fact_measurements
    ADD CONSTRAINT unique_measurement_by_station
        UNIQUE (source_id, station_id, parameter_id, timestamp);

CREATE INDEX idx_fact_measurements_station
    ON fact_measurements (station_id);
