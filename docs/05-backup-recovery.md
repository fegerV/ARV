# Backup and Recovery

## Overview

Vertex AR implements a comprehensive backup strategy for both PostgreSQL database and storage content to ensure business continuity and disaster recovery.

## Backup Strategy

### PostgreSQL Database

#### Continuous WAL Archiving
- Write-Ahead Logs (WAL) are continuously archived to persistent storage
- Point-in-time recovery (PITR) capability with 1-minute RPO
- Automated archiving via `archive_command` in PostgreSQL configuration

#### Scheduled Logical Backups
- Daily `pg_dump` logical backups at 2:00 AM UTC
- Stored in multiple locations (local + cloud)
- Retention: 30 days with weekly full backups kept forever

#### Physical Backups
- Weekly `pg_basebackup` physical backups on Sundays
- Stored in compressed format
- Used for faster restore operations

### Storage Content

#### Local Storage
- Automatic rsync to backup server every 6 hours
- Incremental backups with hard links to save space
- Retention: 7 daily, 4 weekly, 12 monthly snapshots

#### MinIO Storage
- Built-in replication to secondary MinIO cluster
- Versioning enabled for all objects
- Lifecycle policies for automated tiering

#### Yandex Disk Storage
- Daily sync to backup folder using official CLI
- Revision history maintained by Yandex Disk
- Cross-region replication enabled

## Backup Implementation

### PostgreSQL Backup Scripts

Daily logical backup script (`scripts/backup-daily.sh`):

```bash
#!/bin/bash
set -euo pipefail

# Environment
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/vertex_ar_${DATE}.sql.gz"

# Create backup
pg_dump -U vertex_ar -h postgres vertex_ar | gzip > "$BACKUP_FILE"

# Verify backup
gunzip -t "$BACKUP_FILE"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "vertex_ar_*.sql.gz" -mtime +30 -delete

# Notify success
echo "Backup completed: $BACKUP_FILE"
```

Weekly physical backup script (`scripts/backup-weekly.sh`):

```bash
#!/bin/bash
set -euo pipefail

# Environment
BACKUP_DIR="/backups/postgres/basebackups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${DATE}"

# Create physical backup
pg_basebackup -U replicator -h postgres -D "$BACKUP_PATH" -Ft -z

# Create backup label
echo "Weekly base backup ${DATE}" > "${BACKUP_PATH}/backup_label"

# Cleanup old backups (keep 12 weeks)
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +84 -exec rm -rf {} +
```

### Storage Backup Scripts

Local storage backup (`scripts/backup-storage.sh`):

```bash
#!/bin/bash
set -euo pipefail

# Environment
SOURCE_DIR="/app/storage/content"
BACKUP_DIR="/backups/storage"
DATE=$(date +%Y%m%d)

# Create incremental backup with hard links
rsync -a --link-dest="${BACKUP_DIR}/latest" \
      "${SOURCE_DIR}/" \
      "${BACKUP_DIR}/$DATE/"

# Update latest symlink
ln -sfn "$DATE" "${BACKUP_DIR}/latest"

# Cleanup old backups (keep 7 days, 4 weeks, 12 months)
# Daily: keep 7 days
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +7 -a -mtime -30 -exec rm -rf {} +
# Weekly: keep 4 weeks (Sundays only)
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +30 -a -mtime -365 \( ! -name "*$(date -d '30 days ago' +%u)*" \) -exec rm -rf {} +
# Monthly: keep 12 months
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +365 -exec rm -rf {} +
```

## Backup Verification

### Automated Testing

Daily backup verification (`scripts/verify-backup.sh`):

```bash
#!/bin/bash
set -euo pipefail

# Environment
BACKUP_DIR="/backups/postgres"
LATEST_BACKUP=$(ls -t ${BACKUP_DIR}/vertex_ar_*.sql.gz | head -1)

# Restore to temporary database
createdb -U vertex_ar -h postgres vertex_ar_verify
gunzip -c "$LATEST_BACKUP" | psql -U vertex_ar -h postgres vertex_ar_verify

# Run basic checks
psql -U vertex_ar -h postgres -d vertex_ar_verify -c "SELECT COUNT(*) FROM companies;"
psql -U vertex_ar -h postgres -d vertex_ar_verify -c "SELECT COUNT(*) FROM projects;"

# Cleanup
dropdb -U vertex_ar -h postgres vertex_ar_verify

echo "Backup verification completed successfully"
```

### Manual Verification

```bash
# Check backup integrity
gzip -t /backups/postgres/vertex_ar_20251207.sql.gz

# List backup contents
gunzip -c /backups/postgres/vertex_ar_20251207.sql.gz | head -20

# Check WAL archive status
ls -la /var/lib/postgresql/wal_archive/
```

## Recovery Procedures

### PostgreSQL Recovery

#### Point-in-Time Recovery (PITR)

1. Stop PostgreSQL service:
```bash
docker compose stop postgres
```

2. Prepare recovery configuration:
```bash
# Create recovery.signal file
touch /var/lib/postgresql/data/recovery.signal

# Create standby.signal for streaming
touch /var/lib/postgresql/data/standby.signal

# Configure recovery target in postgresql.conf
echo "recovery_target_time = '2025-12-07 14:30:00'" >> /var/lib/postgresql/data/postgresql.conf
```

3. Start PostgreSQL:
```bash
docker compose start postgres
```

#### Full Database Restore

1. Stop application services:
```bash
docker compose stop app celery-worker celery-beat
```

2. Drop and recreate database:
```bash
docker compose exec postgres dropdb -U vertex_ar vertex_ar
docker compose exec postgres createdb -U vertex_ar vertex_ar
```

3. Restore from backup:
```bash
# Logical restore
gunzip -c /backups/postgres/vertex_ar_20251207.sql.gz | \
docker compose exec -T postgres psql -U vertex_ar vertex_ar

# Or physical restore (requires stopping postgres)
# 1. Stop postgres container
# 2. Replace data directory contents
# 3. Start postgres container
```

4. Run migrations if needed:
```bash
docker compose exec app alembic upgrade head
```

5. Start services:
```bash
docker compose start app celery-worker celery-beat
```

### Storage Recovery

#### Local Storage Recovery

1. Identify the backup to restore:
```bash
ls -la /backups/storage/
```

2. Restore files:
```bash
# Stop application
docker compose stop app

# Restore from backup
rsync -av /backups/storage/20251207/ /app/storage/content/

# Fix permissions
chown -R 1000:1000 /app/storage/content/

# Start application
docker compose start app
```

#### MinIO Recovery

1. Access MinIO console:
```bash
# Forward MinIO port
kubectl port-forward svc/minio 9001:9001

# Access via browser: http://localhost:9001
```

2. Restore from replication or version history:
- Navigate to bucket
- Select object
- Choose version to restore
- Click "Restore" or download specific version

#### Yandex Disk Recovery

1. Install Yandex Disk CLI:
```bash
# Download from official website
wget https://disk.yandex.ru/download/cli/ydcmd-linux-amd64
chmod +x ydcmd-linux-amd64
sudo mv ydcmd-linux-amd64 /usr/local/bin/ydcmd
```

2. Authenticate:
```bash
ydcmd token
```

3. Restore files:
```bash
# List backups
ydcmd ls /Backup/VertexAR/

# Download specific backup
ydcmd get /Backup/VertexAR/storage_20251207.tar.gz

# Extract
tar -xzf storage_20251207.tar.gz -C /app/storage/content/
```

## Disaster Recovery Plan

### RTO/RPO Targets

- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 1 hour

### Recovery Steps

1. **Assessment** (15 minutes)
   - Identify failure type and scope
   - Notify stakeholders
   - Activate DR team

2. **Infrastructure Recovery** (1 hour)
   - Provision new servers/containers
   - Restore network connectivity
   - Configure load balancers

3. **Database Recovery** (1.5 hours)
   - Restore from latest backup
   - Apply WAL logs for PITR
   - Verify data integrity

4. **Application Recovery** (1 hour)
   - Deploy application containers
   - Restore storage content
   - Configure environment variables

5. **Validation** (30 minutes)
   - Run health checks
   - Test critical functionality
   - Validate data consistency

6. **Go Live** (15 minutes)
   - Switch DNS/load balancer
   - Monitor system performance
   - Notify users

### Contact Information

- **Primary DR Coordinator**: admin@vertexar.com
- **Secondary Contact**: ops@vertexar.com
- **Telegram Emergency Channel**: @VertexARDR
- **Phone**: +1-555-DR-ALERT

## Monitoring and Alerts

### Backup Monitoring

- Daily backup success/failure alerts via email and Telegram
- Backup size and duration metrics in Prometheus
- Automated verification results in Grafana dashboard

### Recovery Monitoring

- Recovery time tracking
- Data consistency checks
- Application health monitoring during restore

## Testing Schedule

- **Weekly**: Backup verification scripts
- **Monthly**: Full restore drill (non-production)
- **Quarterly**: Disaster recovery simulation
- **Annually**: Full production DR test