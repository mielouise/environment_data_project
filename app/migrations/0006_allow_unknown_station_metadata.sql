ALTER TABLE dim_stations
    ALTER COLUMN station_name DROP NOT NULL,
    ALTER COLUMN station_type DROP NOT NULL,
    ALTER COLUMN country_code DROP NOT NULL,
    ALTER COLUMN latitude DROP NOT NULL,
    ALTER COLUMN longitude DROP NOT NULL,
    ALTER COLUMN valid_from DROP NOT NULL;
