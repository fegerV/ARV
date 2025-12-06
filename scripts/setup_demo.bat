@echo off
REM scripts/setup_demo.bat
echo 🚀 Creating Vertex AR Demo Environment...

REM 1. Apply migrations
echo 📦 Applying database migrations...
docker-compose exec app alembic upgrade head

REM 2. Create first admin user
echo 👤 Creating admin user...
docker-compose exec app python create_admin_user.py

REM 3. Create demo data
echo 🎬 Creating demo data...
docker-compose exec app python scripts/create_demo_data.py

REM 4. Generate demo markers
echo 🏷️  Generating demo markers...
docker-compose exec app python scripts/generate_demo_markers.py

REM 5. Generate demo statistics
echo 📊 Generating demo statistics...
docker-compose exec app python scripts/generate_demo_statistics.py

echo ✅ Demo environment ready!
echo Open http://localhost:3000 in your browser
echo Login with: admin@vertexar.com / admin123

echo.
echo 🎯 Demo Content Summary:
echo 🏢 1 Default Company (Vertex AR)
echo 🏢 5 Client Companies
echo 📁 6 Projects
echo 🎬 6 AR Portraits with Markers
echo 📹 8+ Videos
echo 📊 View Statistics
echo 🔗 QR Codes Ready

pause