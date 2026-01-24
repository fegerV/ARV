#!/bin/bash
set -euo pipefail

BASEBACKUP_DIR="/backups/base"
WAL_ARCHIVE="/backups/wal_archive"

# Daily base backup
pg_basebackup -h localhost -U vertex_ar -D "$BASEBACKUP_DIR/base_$(date +%Y%m%d)" \
  -Ft -z -P --wal-method=stream

# Sync WAL to S3
aws s3 sync "$WAL_ARCHIVE" "s3://${BACKUP_S3_BUCKET}/wal/"
