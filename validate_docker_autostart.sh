#!/bin/bash

# Validation script for Docker autostart migration implementation
# This script validates that all components are properly configured

echo "🔍 Validating Docker Autostart Migration Implementation..."
echo

# Check 1: entrypoint.sh exists and is executable
echo "1️⃣ Checking entrypoint.sh..."
if [ -f "entrypoint.sh" ]; then
    if [ -x "entrypoint.sh" ]; then
        echo "   ✅ entrypoint.sh exists and is executable"
    else
        echo "   ❌ entrypoint.sh exists but is not executable"
        exit 1
    fi
else
    echo "   ❌ entrypoint.sh does not exist"
    exit 1
fi

# Check 2: entrypoint.sh syntax is valid
echo "2️⃣ Checking entrypoint.sh syntax..."
if bash -n entrypoint.sh; then
    echo "   ✅ entrypoint.sh syntax is valid"
else
    echo "   ❌ entrypoint.sh has syntax errors"
    exit 1
fi

# Check 3: seed script exists and has valid Python syntax
echo "3️⃣ Checking seed script..."
if [ -f "scripts/seed_db.py" ]; then
    if python -m py_compile scripts/seed_db.py 2>/dev/null; then
        echo "   ✅ scripts/seed_db.py exists and has valid Python syntax"
    else
        echo "   ❌ scripts/seed_db.py has Python syntax errors"
        exit 1
    fi
else
    echo "   ❌ scripts/seed_db.py does not exist"
    exit 1
fi

# Check 4: Dockerfile has proper ENTRYPOINT configuration
echo "4️⃣ Checking Dockerfile ENTRYPOINT..."
if grep -q "ENTRYPOINT \[\"/usr/local/bin/entrypoint.sh\"\]" Dockerfile; then
    echo "   ✅ Dockerfile has correct ENTRYPOINT configuration"
else
    echo "   ❌ Dockerfile missing or has incorrect ENTRYPOINT"
    exit 1
fi

# Check 5: Dockerfile copies entrypoint script
echo "5️⃣ Checking Dockerfile entrypoint copy..."
if grep -q "COPY entrypoint.sh /usr/local/bin/" Dockerfile; then
    echo "   ✅ Dockerfile copies entrypoint.sh to correct location"
else
    echo "   ❌ Dockerfile does not copy entrypoint.sh"
    exit 1
fi

# Check 6: Dockerfile sets executable permissions
echo "6️⃣ Checking Dockerfile executable permissions..."
if grep -q "chmod +x /usr/local/bin/entrypoint.sh" Dockerfile; then
    echo "   ✅ Dockerfile sets executable permissions on entrypoint.sh"
else
    echo "   ❌ Dockerfile does not set executable permissions"
    exit 1
fi

# Check 7: docker-compose.yml has health check dependencies
echo "7️⃣ Checking docker-compose.yml health dependencies..."
if grep -q "condition: service_healthy" docker-compose.yml; then
    echo "   ✅ docker-compose.yml has proper health check dependencies"
else
    echo "   ❌ docker-compose.yml missing health check dependencies"
    exit 1
fi

# Check 8: PostgreSQL health check configuration
echo "8️⃣ Checking PostgreSQL health check..."
if grep -q "pg_isready -U vertex_ar" docker-compose.yml; then
    echo "   ✅ PostgreSQL has proper health check configuration"
else
    echo "   ❌ PostgreSQL missing health check configuration"
    exit 1
fi

# Check 9: alembic is available (in virtual environment)
echo "9️⃣ Checking alembic availability..."
if source .venv/bin/activate 2>/dev/null && which alembic >/dev/null 2>&1; then
    echo "   ✅ alembic is available in virtual environment"
else
    echo "   ❌ alembic is not available"
    exit 1
fi

# Check 10: Docker Compose configuration is valid
echo "🔟 Checking docker-compose.yml syntax..."
if docker compose config --quiet >/dev/null 2>&1; then
    echo "   ✅ docker-compose.yml has valid syntax"
else
    echo "   ❌ docker-compose.yml has syntax errors"
    exit 1
fi

echo
echo "🎉 All validation checks passed!"
echo "✅ Docker autostart migration implementation is ready for deployment."
echo
echo "📋 Next steps:"
echo "   1. Run: docker compose build"
echo "   2. Run: docker compose up"
echo "   3. Watch logs: docker compose logs app"
echo
echo "📝 Expected startup sequence:"
echo "   1. PostgreSQL health check"
echo "   2. Database migrations (alembic upgrade head)"
echo "   3. Data seeding (admin user & default company)"
echo "   4. Application startup (uvicorn)"