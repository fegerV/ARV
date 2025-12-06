#!/bin/bash
# scripts/setup_demo.sh
echo "🚀 Creating Vertex AR Demo Environment..."

# Check if we're running in Windows or Linux environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows with Git Bash or similar
    DC_CMD="docker-compose"
else
    # Linux or WSL
    DC_CMD="docker compose"
fi

# 1. Apply migrations
echo "📦 Applying database migrations..."
$DC_CMD exec app alembic upgrade head

# 2. Create first admin user
echo "👤 Creating admin user..."
$DC_CMD exec app python create_admin_user.py

# 3. Create demo data
echo "🎬 Creating demo data..."
$DC_CMD exec app python scripts/create_demo_data.py

# 4. Generate demo markers
echo "🏷️  Generating demo markers..."
$DC_CMD exec app python scripts/generate_demo_markers.py

# 5. Generate demo statistics
echo "📊 Generating demo statistics..."
$DC_CMD exec app python scripts/generate_demo_statistics.py

echo "✅ Demo environment ready!"
echo "Open http://localhost:3000 in your browser"
echo "Login with: admin@vertexar.com / admin123"

echo ""
echo "🎯 Demo Content Summary:"
echo "🏢 1 Default Company (Vertex AR)"
echo "🏢 5 Client Companies"
echo "📁 6 Projects"
echo "🎬 6 AR Portraits with Markers"
echo "📹 8+ Videos"
echo "📊 View Statistics"
echo "🔗 QR Codes Ready"