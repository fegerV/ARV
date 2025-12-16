# Setup Guide

This document provides comprehensive instructions for setting up the ARVlite project both for local development and using Docker.

## LOCAL DEVELOPMENT

### System Requirements
- **Node.js**: Version 18.x or higher (recommended: LTS version)
- **Python**: Version 3.10 or higher
- **PostgreSQL**: Version 12 or higher
- **Redis**: Latest stable version (recommended: 7.x)

### Installation Steps

#### 1. Clone the repository
```bash
git clone <repository-url>
cd ARVlite
```

#### 2. Install Backend Dependencies
Navigate to the ARV directory and install Python dependencies:
```bash
cd ARV
pip install -r requirements.txt
```

#### 3. Install Frontend Dependencies
Navigate to the frontend directory and install Node.js dependencies:
```bash
cd ARV/frontend
npm install
```

#### 4. Configure Environment Variables
Create a `.env` file in the ARV directory based on the example:
```bash
cp .env.example .env
```

Edit the `.env` file with your specific configurations:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/arvlitedb
TEST_DATABASE_URL=postgresql://username:password@localhost:5432/arvlitetest

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security Settings
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OAuth Settings (Optional)
YANDEX_CLIENT_ID=your_yandex_client_id
YANDEX_CLIENT_SECRET=your_yandex_client_secret

# Storage Settings
STORAGE_PROVIDER=local  # Options: local, s3, yandex
LOCAL_STORAGE_PATH=./storage

# Email Settings (Optional)
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
FROM_EMAIL=no-reply@arvlite.local
```

#### 5. Initialize Database
Run database initialization script to create tables and seed data:
```bash
cd ARV
python init_db.py
```

Alternatively, you can manually run migrations:
```bash
# Run migrations
alembic upgrade head

# Seed initial data (if needed)
python check_seed_data.py
```

#### 6. Start Backend Server
From the ARV directory:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 7. Start Frontend Server
From the ARV/frontend directory:
```bash
cd ARV/frontend
npm run dev
```

#### 8. Verification
Once both servers are running, verify the following URLs work:
- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Frontend App**: http://localhost:5173 (Vite dev server)
- **Backend Health Check**: http://localhost:8000/health

## DOCKER DEVELOPMENT

### Prerequisites
- Docker Engine version 20.10 or higher
- Docker Compose version 2.0 or higher

### Docker Setup Steps

#### 1. Install Docker and Docker Compose
Follow the official Docker installation guide for your OS:
- [Docker Desktop for Windows/Mac](https://www.docker.com/products/docker-desktop/)
- [Docker Engine for Linux](https://docs.docker.com/engine/install/)

#### 2. Understanding docker-compose.yml
The docker-compose.yml file defines multiple services:
- **db**: PostgreSQL database container
- **redis**: Redis cache container
- **backend**: FastAPI application container
- **frontend**: Vite development server container
- **nginx**: Reverse proxy (in production config)

#### 3. Full Start with Docker Compose
From the ARV directory, run:
```bash
cd ARV
docker compose up -d
```

This command starts all services in detached mode.

#### 4. Available Services and Ports
- **Frontend**: http://localhost:3000 (proxied through nginx)
- **Backend API**: http://localhost:8000/docs
- **Database**: localhost:5432 (internal: db:5432)
- **Redis**: localhost:6379 (internal: redis:6379)

#### 5. View Logs
To see logs from all services:
```bash
docker compose logs -f
```

To see logs from a specific service:
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

#### 6. Restart Individual Service
To restart a specific service:
```bash
docker compose restart backend
docker compose restart frontend
```

#### 7. Clean Docker Volumes
To completely reset the environment (removes all data):
```bash
# Stop all containers
docker compose down

# Remove volumes
docker compose down -v

# Rebuild and start
docker compose up --build -d
```

## TROUBLESHOOTING

### Port Already in Use
**Problem**: Error indicating port is already in use.
**Solution**:
- Check what's using the port: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Mac/Linux)
- Kill the process: `taskkill /PID <pid> /F` (Windows) or `kill -9 <pid>` (Mac/Linux)
- Or change ports in your configuration files

### PostgreSQL Connection Error
**Problem**: Cannot connect to PostgreSQL database.
**Solution**:
- Verify PostgreSQL is running: `pg_ctl status` or check Windows Services
- Check credentials in your `.env` file
- Ensure the database exists: `psql -U username -c "\l"` to list databases
- Try connecting manually: `psql -U username -d arvlitedb`

### Redis Connection Error
**Problem**: Cannot connect to Redis server.
**Solution**:
- Verify Redis is running: `redis-cli ping` should return "PONG"
- Check Redis URL in your `.env` file
- On Windows, install Redis using Chocolatey: `choco install redis-64`
- On Mac, install using Homebrew: `brew install redis`

### npm/pip Install Errors
**Problem**: Dependency installation fails.
**Solution**:
- Update npm: `npm install -g npm@latest`
- Clear npm cache: `npm cache clean --force`
- Use virtual environment for Python: `python -m venv venv && source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- Upgrade pip: `pip install --upgrade pip`

### Migrations Not Applying
**Problem**: Alembic migrations fail or don't apply.
**Solution**:
- Check migration files exist in `ARV/alembic/versions/`
- Run migrations manually: `alembic upgrade head`
- Check database connection string in `app/core/config.py`
- Reset migrations if needed: `alembic downgrade base` then `alembic upgrade head`

### Frontend Not Seeing Backend
**Problem**: Frontend makes requests to backend but gets errors.
**Solution**:
- Verify backend is running on http://localhost:8000
- Check CORS settings in `app/main.py`
- In development, frontend proxy should forward API calls to backend
- Check network tab in browser dev tools for specific error messages
- Ensure both servers are running before testing functionality

### Additional Troubleshooting Commands
```bash
# Check if services are running
docker ps

# Check container logs
docker logs <container-name>

# Execute commands inside container
docker exec -it <container-name> bash

# Check if database is ready
python check_db.py

# Run health checks
python check_containers.py