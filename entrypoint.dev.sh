#!/bin/bash
# Development entry point script that runs database migrations before starting the application

set -e

echo "Running in development mode..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U vertex_ar; do
 >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing"

# Run database migrations
echo "Running database migrations..."
cd /app
alembic upgrade head

# Check if alembic revision is needed (if there are model changes without migrations)
echo "Checking for pending migrations..."
python -c "
import sys
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

# Get current DB revision
config = Config('alembic.ini')
engine = create_engine('${DATABASE_URL:-postgresql+asyncpg://vertex_ar:password@postgres:5432/vertex_ar}')
with engine.connect() as connection:
    context = MigrationContext.configure(connection)
    current_rev = context.get_current_revision()

# Get latest migration in script directory
script = ScriptDirectory.from_config(config)
latest_rev = script.get_current_head()

if current_rev != latest_rev:
    print('New models detected, but no migration created yet.')
    print('Consider running: docker-compose run app alembic revision --autogenerate -m \"description\"')
else:
    print('Database is up to date.')
"

# Start the application with reload enabled
echo "Starting application in development mode..."
exec "$@"