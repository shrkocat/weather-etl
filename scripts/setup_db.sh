#!/usr/bin/env bash
# Creates the local Postgres database (if needed) and applies sql/schema.sql.
# Requires `psql` and a running Postgres server (see docker/docker-compose.yml
# if you'd rather not install Postgres locally).
set -euo pipefail

cd "$(dirname "$0")/.."

: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=postgres}"
: "${POSTGRES_DB:=weather_etl}"

echo "Creating database '$POSTGRES_DB' (if it doesn't already exist)..."
PGPASSWORD="${POSTGRES_PASSWORD:-}" createdb \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
    "$POSTGRES_DB" 2>/dev/null || echo "Database already exists, continuing."

echo "Applying schema..."
PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f sql/schema.sql

echo "Done. Database '$POSTGRES_DB' is ready."
