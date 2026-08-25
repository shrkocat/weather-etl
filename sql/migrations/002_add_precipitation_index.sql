-- Migration 002: add an index to support reports that filter/sort on
-- precipitation (e.g. "rainiest days this month" dashboard query).

CREATE INDEX IF NOT EXISTS idx_weather_precipitation
    ON weather_observations (precipitation_mm);
