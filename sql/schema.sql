-- Base schema for the weather ETL pipeline.
-- This file represents the CURRENT state of the schema, achieved by
-- applying sql/migrations/*.sql in order. For a fresh database you can
-- run this file directly; for an existing one, apply new migrations.

CREATE TABLE IF NOT EXISTS weather_observations (
    id                  BIGSERIAL PRIMARY KEY,
    location_name       VARCHAR(100)     NOT NULL,
    observation_time    TIMESTAMPTZ      NOT NULL,
    temperature_celsius NUMERIC(5, 2),
    humidity_pct        NUMERIC(5, 2),
    wind_speed_kmh       NUMERIC(6, 2),
    precipitation_mm    NUMERIC(6, 2),
    latitude            NUMERIC(9, 6),
    longitude           NUMERIC(9, 6),
    fetched_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),

    CONSTRAINT uq_location_observation UNIQUE (location_name, observation_time)
);

CREATE INDEX IF NOT EXISTS idx_weather_location
    ON weather_observations (location_name);

CREATE INDEX IF NOT EXISTS idx_weather_observation_time
    ON weather_observations (observation_time);
