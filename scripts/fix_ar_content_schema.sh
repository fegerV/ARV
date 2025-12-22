#!/bin/bash

# Script to apply AR Content schema fixes and run tests
# This script ensures that all required columns and timestamps are present

set -e

echo "🚀 AR Content Schema Fix and Test Script"
echo "=========================================="

# Function to check if PostgreSQL is available
check_postgres() {
    echo "🔍 Checking PostgreSQL connection..."
    if python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'vertex_ar'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )
    conn.close()
    print('✅ PostgreSQL connection successful')
    exit(0)
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    exit(1)
"; then
        return 0
    else
        return 1
    fi
}

# Function to run Alembic migration
run_migration() {
    echo "🔄 Running Alembic migration..."
    if alembic upgrade head; then
        echo "✅ Migration completed successfully"
        return 0
    else
        echo "❌ Migration failed"
        return 1
    fi
}

# Function to run schema test
run_schema_test() {
    echo "🧪 Running AR Content schema test..."
    if python3 test_ar_content_schema.py; then
        echo "✅ Schema test passed"
        return 0
    else
        echo "❌ Schema test failed"
        return 1
    fi
}

# Function to create a simple backup of current state
create_backup() {
    echo "💾 Creating database backup..."
    backup_file="backup_ar_content_$(date +%Y%m%d_%H%M%S).sql"
    
    if pg_dump -h localhost -p 5432 -U postgres -d vertex_ar -t ar_content > "$backup_file" 2>/dev/null; then
        echo "✅ Backup created: $backup_file"
        return 0
    else
        echo "⚠️  Backup failed (continuing anyway)"
        return 0
    fi
}

# Main execution
main() {
    echo "Starting AR Content schema fix process..."
    
    # Check if we can connect to PostgreSQL
    if ! check_postgres; then
        echo "❌ Cannot connect to PostgreSQL. Please check your database configuration."
        exit 1
    fi
    
    # Create backup (optional)
    create_backup
    
    # Run the migration
    if ! run_migration; then
        echo "❌ Migration failed. Please check the error messages above."
        exit 1
    fi
    
    # Run the schema test
    if ! run_schema_test; then
        echo "❌ Schema test failed. Please check the test output above."
        exit 1
    fi
    
    echo ""
    echo "🎉 AR Content schema fix completed successfully!"
    echo "✅ All required columns and timestamps have been added."
    echo "✅ AR Content creation is now working properly."
    echo ""
    echo "You can now:"
    echo "1. Create AR content through the API"
    echo "2. Upload images and videos"
    echo "3. Generate AR markers"
    echo "4. Use the admin interface"
}

# Run main function
main "$@"