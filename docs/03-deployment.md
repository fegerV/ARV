# Deployment

## Overview

Vertex AR uses Docker Compose for both development and production deployments. The deployment process includes building containers, configuring environment variables, applying database migrations, and starting services.

## Prerequisites

### Production Environment

- **Operating System**: Ubuntu 22.04 LTS or CentOS 8+
- **Docker**: 24.0+
- **Docker Compose**: V2+
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 50GB minimum (100GB+ recommended)
- **CPU**: 4 cores minimum (8 cores recommended)

### DNS and SSL

- Domain name pointing to server IP
- SSL certificate (Let's Encrypt or commercial)
- Reverse proxy configuration (Nginx/Apache)

## Environment Configuration

### Environment Variables

Create `.env` file based on `.env.example`:

```bash
# Copy example configuration
cp .env.example .env

# Edit with production values
nano .env
```

Key production variables:

```env
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql+asyncpg://vertex_ar:secure_password@postgres:5432/vertex_ar
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-very-long-random-secret-key-here
CORS_ORIGINS=https://yourdomain.com

# Storage
STORAGE_TYPE=minio  # or yandex_disk
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key

# Notifications
SMTP_HOST=smtp.your-email-provider.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yourdomain.com
SMTP_PASSWORD=your-email-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com

TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ADMIN_CHAT_ID=your-telegram-chat-id

# External Services
YANDEX_OAUTH_CLIENT_ID=your-yandex-client-id
YANDEX_OAUTH_CLIENT_SECRET=your-yandex-client-secret
```

## Production Deployment

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/fegerV/ARV.git
cd vertex-ar

# Create environment file
cp .env.example .env
# Edit .env with production values

# Create storage directories
mkdir -p storage/content
mkdir -p backups/postgres
mkdir -p backups/storage

# Set proper permissions
chown -R 1000:1000 storage/
chown -R 1000:1000 backups/
```

### 2. SSL Certificate Setup

Using Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo apt update
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to project directory
sudo mkdir -p nginx/certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/certs/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/certs/key.pem
sudo chown $USER:$USER nginx/certs/*
```

### 3. Docker Configuration

Update `docker-compose.yml` for production:

```yaml
version: '3.8'
services:
  postgres:
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups/postgres:/backups:rw
    environment:
      POSTGRES_DB: vertex_ar
      POSTGRES_USER: vertex_ar
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vertex_ar"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  app:
    build: .
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./storage/content:/app/storage/content
      - ./backups/storage:/backups/storage
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      # ... other environment variables
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  celery-worker:
    build: .
    restart: unless-stopped
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    depends_on:
      app:
        condition: service_started
    volumes:
      - ./storage/content:/app/storage/content
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      # ... other environment variables

  celery-beat:
    build: .
    restart: unless-stopped
    command: celery -A app.tasks.celery_app beat --loglevel=info
    depends_on:
      app:
        condition: service_started
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      # ... other environment variables

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

### 4. Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # HTTP server - redirect to HTTPS
    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # API proxy
        location /api/ {
            proxy_pass http://app/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check endpoint
        location /api/health/ {
            proxy_pass http://app/api/health/;
            proxy_set_header Host $host;
        }

        # Static files
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    }
}
```

### 5. Build and Deploy

```bash
# Build images
docker compose build

# Start services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 6. Database Setup

```bash
# Apply database migrations
docker compose exec app alembic upgrade head

# Create admin user
docker compose exec app python scripts/create_admin_user.py

# Seed initial data (optional)
docker compose exec app python scripts/create_demo_data.py
```

## Scaling

### Horizontal Scaling

For high-traffic deployments:

```yaml
# docker-compose.production.yml
version: '3.8'
services:
  app:
    deploy:
      replicas: 4  # Scale API instances
  
  celery-worker:
    deploy:
      replicas: 6  # Scale background workers
  
  postgres:
    # Use PostgreSQL clustering solution like Patroni
```

### Resource Allocation

Recommended resource allocation:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
  
  celery-worker:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## Backup and Monitoring

### Enable Automated Backups

Add cron jobs for automated backups:

```bash
# Edit crontab
crontab -e

# Add backup jobs
0 2 * * * cd /path/to/vertex-ar && docker compose exec app /app/scripts/backup-daily.sh
0 3 * * 0 cd /path/to/vertex-ar && docker compose exec app /app/scripts/backup-weekly.sh
0 */6 * * * cd /path/to/vertex-ar && /app/scripts/backup-storage.sh
```

### Monitoring Setup

Ensure monitoring services are running:

```bash
# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access Grafana
open https://yourdomain.com:3001

# Access Prometheus
open https://yourdomain.com:9090
```

## Updates and Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Build new images
docker compose build

# Stop services gracefully
docker compose stop

# Start updated services
docker compose up -d

# Apply migrations if needed
docker compose exec app alembic upgrade head
```

### Zero-Downtime Deployments

For production environments requiring zero downtime:

```bash
# Use blue-green deployment strategy
# 1. Deploy new version to green environment
# 2. Test thoroughly
# 3. Switch traffic from blue to green
# 4. Decommission blue environment
```

### Maintenance Windows

Schedule maintenance during low-traffic periods:

```bash
# Check traffic patterns
docker compose exec prometheus curl http://localhost:9090/api/v1/query?query=sum(rate(api_request_count_total[1h]))

# Schedule maintenance
echo "Maintenance window: 02:00-04:00 UTC" > MAINTENANCE_NOTICE
```

## Security Considerations

### Network Security

- Restrict external access to only necessary ports (80, 443)
- Use internal networks for service communication
- Implement firewall rules

### Data Security

- Encrypt data at rest and in transit
- Regular security audits
- Keep dependencies updated

### Access Control

- Use strong authentication for admin interfaces
- Implement rate limiting
- Regular credential rotation

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service logs
docker compose logs app

# Check dependencies
docker compose logs postgres redis

# Verify environment variables
docker compose exec app env
```

#### Database Connection Issues

```bash
# Test database connectivity
docker compose exec app pg_isready -h postgres -U vertex_ar

# Check database logs
docker compose logs postgres
```

#### Performance Problems

```bash
# Monitor resource usage
docker stats

# Check application metrics
curl https://yourdomain.com/api/health/metrics

# Profile slow queries
docker compose exec postgres psql -U vertex_ar -c "EXPLAIN ANALYZE SELECT * FROM companies WHERE active = true;"
```

### Recovery Procedures

#### Rollback Deployment

```bash
# Stop current services
docker compose down

# Checkout previous version
git checkout HEAD~1

# Start previous version
docker compose up -d
```

#### Database Recovery

See [Backup and Recovery](05-backup-recovery.md) documentation for detailed procedures.