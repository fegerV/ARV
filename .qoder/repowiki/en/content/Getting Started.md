# Getting Started

<cite>
**Referenced Files in This Document**   
- [README.md](file://README.md)
- [.env.example](file://.env.example)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.override.yml](file://docker-compose.override.yml)
- [Dockerfile](file://Dockerfile)
- [app/core/config.py](file://app/core/config.py)
- [app/main.py](file://app/main.py)
- [app/core/database.py](file://app/core/database.py)
</cite>

## Table of Contents
1. [Prerequisites Installation](#prerequisites-installation)
2. [Platform Setup Process](#platform-setup-process)
3. [Configuration Files Overview](#configuration-files-overview)
4. [Development vs Production Configuration](#development-vs-production-configuration)
5. [Common Setup Issues and Troubleshooting](#common-setup-issues-and-troubleshooting)
6. [Verification and Access](#verification-and-access)

## Prerequisites Installation

Before setting up the ARV platform, ensure all prerequisites are properly installed on your system. The platform supports both Windows and Linux environments with specific recommendations for each.

### Docker Desktop and WSL2 (Windows)
For Windows users, Docker Desktop with WSL2 backend is required:
1. Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. Install WSL2 (Windows Subsystem for Linux) following Microsoft's official guide
3. Configure Docker Desktop to use the WSL2 backend in Settings > General
4. Verify installation with `docker --version` and `docker compose version`

### Docker and Docker Compose (Linux)
For Linux users, install Docker Engine and Docker Compose separately:
```bash
# Install Docker Engine
sudo apt update && sudo apt install docker.io docker-compose

# Add user to docker group to avoid sudo
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

### Python 3.11+
The ARV platform requires Python 3.11 or higher:
```bash
# Check current version
python3 --version

# Install Python 3.11+ (Ubuntu/Debian)
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### Node.js 18+
Node.js 18 or higher is required for frontend development:
```bash
# Using Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Verify installation
node --version
npm --version
```

**Section sources**
- [README.md](file://README.md#L7-L11)

## Platform Setup Process

Follow these step-by-step instructions to set up the ARV platform.

### Step 1: Clone the Repository
```bash
# Clone the repository
git clone <repository-url>
cd vertex-ar

# Expected output
Cloning into 'vertex-ar'...
remote: Enumerating objects: 1234, done.
remote: Counting objects: 100% (1234/1234), done.
remote: Compressing objects: 100% (890/890), done.
remote: Total 1234 (delta 456), reused 987 (delta 345), pack-reused 0
Receiving objects: 100% (1234/1234), 15.23 MiB | 5.43 MiB/s, done.
Resolving deltas: 100% (456/456), done.
```

### Step 2: Create .env File
```bash
# Copy example environment file
cp .env.example .env

# Verify file creation
ls -la .env
-rw-r--r-- 1 user user 2123 date .env
```

### Step 3: Start Services with Docker Compose
```bash
# Start all services in detached mode
docker compose up -d

# Expected output
[+] Running 6/6
 ⠿ Network vertex-ar-network  Created
 ⠿ Container vertex-ar-postgres  Started
 ⠿ Container vertex-ar-redis  Started
 ⠿ Container vertex-ar-app  Started
 ⠿ Container vertex-ar-celery-worker  Started
 ⠿ Container vertex-ar-nginx  Started

# Verify services are running
docker compose ps
NAME                   COMMAND                  SERVICE             STATUS              PORTS
vertex-ar-app          "uvicorn app.main:ap…"   app                 running             0.0.0.0:8000->8000/tcp
vertex-ar-celery-worker "celery -A app.tasks…"  celery-worker       running
vertex-ar-postgres     "docker-entrypoint.s…"   postgres            running             0.0.0.0:5432->5432/tcp
vertex-ar-redis        "redis-server --maxm…"   redis               running             0.0.0.0:6379->6379/tcp
vertex-ar-nginx        "/docker-entrypoint.…"   nginx               running             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Step 4: Apply Database Migrations
```bash
# Apply all pending database migrations
docker compose exec app alembic upgrade head

# Expected output
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 20240115_103000_initial, initial migration
INFO  [alembic.runtime.migration] Running upgrade 20240115_103000_initial -> 20240116_142000_add_company, add company table
INFO  [alembic.runtime.migration] Running upgrade 20240116_142000_add_company -> 20240117_091500_add_storage, add storage tables
```

### Step 5: Create First Admin User
```bash
# Execute script to create first admin user
docker compose exec app python scripts/create_first_admin.py

# Expected output
INFO:root:Creating first admin user...
INFO:root:Admin user created successfully
INFO:root:Email: admin@vertexar.com
INFO:root:Default password: ChangeMe123! (change immediately after login)
```

**Section sources**
- [README.md](file://README.md#L13-L36)
- [app/core/database.py](file://app/core/database.py#L54-L102)

## Configuration Files Overview

### .env File Configuration
The `.env` file contains critical configuration settings for the ARV platform. Key variables include:

| Variable | Purpose | Default Value | Required |
|--------|--------|---------------|----------|
| DATABASE_URL | PostgreSQL connection string | postgresql+asyncpg://vertex_ar:StrongPassword123@postgres:5432/vertex_ar | Yes |
| REDIS_URL | Redis connection string | redis://redis:6379/0 | Yes |
| SECRET_KEY | JWT authentication key | change-this-to-a-secure-random-key-in-production-min-32-chars | Yes |
| STORAGE_TYPE | Storage backend type | local | Yes |
| ADMIN_EMAIL | First admin user email | admin@vertexar.com | Yes |
| ADMIN_DEFAULT_PASSWORD | Default admin password | ChangeMe123! | Yes |

### Environment Variables Security
Never commit the `.env` file to version control. The `.gitignore` file already includes `.env` to prevent accidental commits. For production deployments, consider using environment variable management tools or secret management systems.

**Section sources**
- [.env.example](file://.env.example#L1-L70)
- [app/core/config.py](file://app/core/config.py#L7-L134)

## Development vs Production Configuration

### docker-compose.yml (Production)
The main `docker-compose.yml` file defines the production configuration with optimized settings:

```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    env_file:
      - .env
    environment:
      DEBUG: "false"
      LOG_LEVEL: "INFO"
      ENVIRONMENT: "production"
    restart: unless-stopped
```

Key production features:
- Multi-worker Uvicorn server for performance
- Production logging level (INFO)
- Disabled debug mode
- Automatic restart policies
- Health checks for service monitoring

### docker-compose.override.yml (Development)
The `docker-compose.override.yml` file extends the base configuration for development:

```yaml
version: '3.8'
services:
  app:
    volumes:
      - .:/app
      - ./storage/content:/app/storage/content
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DEBUG: "true"
      LOG_LEVEL: "DEBUG"
      ENVIRONMENT: "development"
```

Key development features:
- Code hot-reloading for rapid development
- Source code volume mounting for live changes
- Debug mode enabled
- Verbose debug logging
- Port exposure for local debugging

When both files are present, Docker Compose automatically merges them, with the override file taking precedence for conflicting settings.

**Section sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L144)
- [docker-compose.override.yml](file://docker-compose.override.yml#L1-L32)
- [Dockerfile](file://Dockerfile#L1-L53)

## Common Setup Issues and Troubleshooting

### Docker Permission Issues
On Linux systems, users must be added to the docker group to avoid permission errors:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Restart shell or run
newgrp docker

# Test without sudo
docker ps
```

If permission issues persist, verify Docker service status:
```bash
sudo systemctl status docker
sudo systemctl start docker
```

### Environment Variable Configuration Problems
Common issues and solutions:

1. **Missing .env file**: Ensure `.env.example` was copied to `.env`
2. **Incorrect database credentials**: Verify DATABASE_URL matches postgres service configuration
3. **Secret key too short**: Ensure SECRET_KEY is at least 32 characters
4. **Port conflicts**: Check if ports 8000, 5432, 6379 are already in use

### Network Connectivity Problems
If services cannot communicate:

```bash
# Check network connectivity between containers
docker compose exec app ping postgres
docker compose exec app ping redis

# Verify network creation
docker network ls | grep vertex-ar-network

# Inspect container network settings
docker inspect vertex-ar-app | grep -A 10 "NetworkSettings"
```

### Failed Container Startup
Troubleshoot container failures:

```bash
# Check container logs
docker compose logs app
docker compose logs postgres
docker compose logs redis

# Common PostgreSQL issues
# If database fails to start due to permission issues:
sudo chown -R 1000:1000 ./volumes/postgres

# Check disk space
df -h

# Restart specific service
docker compose restart app
```

### Database Connection Issues
When migrations fail or database connections timeout:

```bash
# Verify database service health
docker compose exec postgres pg_isready -U vertex_ar -d vertex_ar

# Check if database is accepting connections
docker compose exec postgres psql -U vertex_ar -d vertex_ar -c "SELECT version();"

# Manual migration execution with verbose output
docker compose exec app alembic upgrade head --sql --autogenerate
```

**Section sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L144)
- [app/main.py](file://app/main.py#L40-L77)
- [app/core/database.py](file://app/core/database.py#L8-L52)

## Verification and Access

After completing the setup, verify the platform is functioning correctly:

```bash
# Check all services are healthy
docker compose ps

# Test API health endpoint
curl -s http://localhost:8000/api/health/status | python -m json.tool

# Expected response:
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00.000000Z",
    "environment": "production",
    "version": "0.1.0"
}

# Access the platform
API: http://localhost:8000
API Documentation: http://localhost:8000/docs
Admin Panel: http://localhost:3000
```

Log in to the admin panel using the credentials created in Step 5. Immediately change the default password after first login for security purposes.

**Section sources**
- [README.md](file://README.md#L32-L35)
- [app/main.py](file://app/main.py#L209-L223)