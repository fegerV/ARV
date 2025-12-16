---
trigger: always_on
alwaysApply: true
---
API Context (Swagger/OpenAPI)
Key Endpoints:
POST /api/companies              # Создать клиентскую компанию
POST /api/projects/{id}/ar-content  # Загрузить AR-контент
POST /api/ar-content/{id}/generate-marker  # NFT маркер
GET  /api/ar/{unique_id}/active-video     # Активное видео для AR
POST /api/ar-content/{id}/videos          # Загрузить видео
GET  /ar/{unique_id}                      # Public AR Viewer
GET  /api/analytics/overview              # Dashboard metrics

Docker Context
docker-compose.yml structure:
services:
  postgres:15-alpine
  redis:7-alpine  
  app:fastapi (uvicorn workers=4)
  celery-worker (2 workers)
  celery-beat
  nginx:alpine
  postgres-backup (cron)
volumes:
  postgres_data
  redis_data
  storage_content (только Vertex AR local)



