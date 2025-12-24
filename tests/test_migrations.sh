#!/bin/bash
# Test script to verify that migrations run correctly on startup

echo "Testing migration startup process..."

# Build the services
echo "Building services..."
docker-compose build

# Start PostgreSQL separately
echo "Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Run migrations manually to test
echo "Running migrations manually to test..."
docker-compose run --rm db-migrate

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Migrations executed successfully!"
else
    echo "Migrations failed!"
    exit 1
fi

# Bring down services
docker-compose down

echo "Migration test completed successfully!"