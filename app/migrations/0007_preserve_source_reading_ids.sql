ALTER TABLE fact_measurements
    ADD COLUMN source_observation_id VARCHAR(100),
    ADD COLUMN source_reading_id VARCHAR(100);

ALTER TABLE fact_measurements
    DROP CONSTRAINT unique_measurement_by_station;

CREATE UNIQUE INDEX unique_measurement_without_source_reading_id
    ON fact_measurements (source_id, station_id, parameter_id, timestamp)
    WHERE source_reading_id IS NULL AND source_id <> 'HERODOT';

CREATE UNIQUE INDEX unique_measurement_by_source_reading_id
    ON fact_measurements (source_id, source_reading_id)
    WHERE source_reading_id IS NOT NULL;
