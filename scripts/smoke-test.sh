#!/bin/bash
# scripts/smoke-test.sh
set -euo pipefail

echo "🚬 Production smoke tests..."

# 1. Health checks
curl -f http://localhost/api/health/status || exit 1

# 2. Database
docker compose exec postgres psql -U vertex_ar -c "SELECT 1" || exit 1

# 3. Redis
docker compose exec redis redis-cli ping || exit 1

# 4. AR Viewer
curl -f http://localhost/ar/test-content || exit 1

# 5. Admin API (requires ADMIN_TOKEN)
if [ -z "${ADMIN_TOKEN:-}" ]; then
  echo "⚠️ ADMIN_TOKEN not set; skipping admin API smoke test"
else
  curl -f -X POST http://localhost/api/companies \
    -H "Authorization: Bearer $ADMIN_TOKEN" || exit 1
fi

echo "✅ All smoke tests passed!"
