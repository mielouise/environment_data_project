CREATE TABLE IF NOT EXISTS dim_sources (
    source_id VARCHAR(50) PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_parameters (
    parameter_id INTEGER PRIMARY KEY,
    parameter_name VARCHAR(100) NOT NULL UNIQUE,
    unit VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_measurements (
    measurement_id SERIAL PRIMARY KEY,
    source_id VARCHAR(50) NOT NULL
        REFERENCES dim_sources(source_id),
    parameter_id INTEGER NOT NULL
        REFERENCES dim_parameters(parameter_id),
    timestamp TIMESTAMPTZ NOT NULL,
    value NUMERIC(10, 2) NOT NULL,
    CONSTRAINT unique_measurement
        UNIQUE (source_id, parameter_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_fact_measurements_timestamp
ON fact_measurements (timestamp);

CREATE INDEX IF NOT EXISTS idx_fact_measurements_source
ON fact_measurements (source_id);

CREATE INDEX IF NOT EXISTS idx_fact_measurements_parameter
ON fact_measurements (parameter_id);

INSERT INTO dim_parameters (
    parameter_id,
    parameter_name,
    unit
)
VALUES
    (1, 'Temperature', '°C'),
    (2, 'Humidity', '%'),
    (3, 'Humidity Past 1 Hour', '%'),
    (4, 'CO2', 'ppm'),
    (5, 'PM2.5', 'μg/m³')
ON CONFLICT (parameter_id)
DO NOTHING;
