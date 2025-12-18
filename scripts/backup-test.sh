#!/bin/bash
set -euo pipefail

LATEST_BACKUP=$(ls -t /backups/postgresql/*.sql.gz | head -1)

# 1. Test gunzip
if ! gunzip -t "$LATEST_BACKUP"; then
  echo "❌ Backup corrupted"; exit 1;
fi

# 2. Test SQL syntax
if ! gunzip -c "$LATEST_BACKUP" | psql --single-transaction --set ON_ERROR_STOP=on -f -; then
  echo "❌ SQL syntax errors"; exit 1;
fi

# 3. Optional: test restore to staging (requires docker-compose.staging.yml)
# docker-compose -f docker-compose.staging.yml exec postgres psql <(gunzip -c "$LATEST_BACKUP")

echo "✅ Backup verified successfully"
