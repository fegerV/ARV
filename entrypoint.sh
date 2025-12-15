#!/bin/bash
# Entry point script that runs database migrations before starting the application

set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U vertex_ar; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed initial data
echo "Seeding initial database data..."
python scripts/seed_db.py

# Start the application
echo "Starting application..."
exec "$@"