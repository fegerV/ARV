#!/bin/bash

# Vertex AR Development Startup Script
# This script starts the development environment with PostgreSQL and the FastAPI app

set -e

echo "🚀 Starting Vertex AR Development Environment"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/bin/python" ] || [ ! -f ".venv/bin/pip" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p storage/content static

# Start PostgreSQL
echo "🐘 Starting PostgreSQL..."
docker compose up postgres -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Apply migrations
echo "🔄 Applying database migrations..."
alembic upgrade head

# Check admin user
echo "👤 Checking admin user..."
python check_admin_user.py

# Start the application
echo "🌟 Starting FastAPI application..."
echo "📱 Admin Panel will be available at: http://localhost:8000/admin/login"
echo "🔑 Credentials: admin@vertexar.com / ChangeMe123!"
echo ""
echo "Press Ctrl+C to stop the application"
echo "=========================================="

DATABASE_URL="postgresql+asyncpg://vertex_ar:password@localhost:5432/vertex_ar" \
MEDIA_ROOT="./storage/content" \
STATIC_DIR="./static" \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload