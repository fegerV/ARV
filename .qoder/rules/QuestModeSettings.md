---
trigger: always_on
alwaysApply: true
---
┌─────────────────────────────────────────────────────────────┐
│ Project Context                                             │
├─────────────────────────────────────────────────────────────┤
│ Project Name:           [Vertex AR B2B Platform           ] │
│ Project Type:           [FastAPI + React + PostgreSQL    ] │
│ Tech Stack:             [Python 3.11 | FastAPI 0.109     ] │
│                         [React 18 | TypeScript | MUI 5   ] │
│                         [Docker Compose | PostgreSQL 15  ] │
│                                                             │
│ Architecture:                                                         │
│ ├── Backend: FastAPI async + SQLAlchemy 2.0 + PostgreSQL PITR       │
│ ├── Frontend: React 18 + TypeScript + MUI 5 + TailwindCSS           │
│ ├── AR Engine: Mind AR 1.2.5 + Three.js 0.158                      │
│ ├── Storage: Local Disk + MinIO + Yandex Disk OAuth                │
│ └── Queue: Celery 5.3 + Redis 7                                    │
│                                                             │
│ Business Domain: B2B SaaS для AR-контента. Рекламные аг-ва  │
│ загружают изображения+видео → генерируем NFT markers + QR  │
│ → клиенты печатают → конечные пользователи сканируют       │
└─────────────────────────────────────────────────────────────┘

Project Context
Project Name: Vertex AR B2B Platform
Short Name: vertex-ar

Primary Language: Python 3.11
Secondary Language: TypeScript

Framework: FastAPI 0.109 (async-first)
Database: PostgreSQL 15 + SQLAlchemy 2.0 async
ORM Pattern: Repository pattern + SQLAlchemy 2.0 selectinload

File Structure
Copy-paste в поле "File Structure":
vertex-ar/
├── app/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── core/                      # config.py, database.py, security.py
│   ├── models/                    # SQLAlchemy models (companies, projects, ar_content)
│   ├── schemas/                   # Pydantic v2 schemas
│   ├── api/routes/                # companies.py, projects.py, ar_content.py
│   ├── services/                  # storage/, video_scheduler.py, marker_generator.py
│   └── tasks/                     # celery_app.py, marker_tasks.py
├── frontend/                      # React 18 + TypeScript + Vite
├── docker-compose.yml
├── alembic/
└── storage/content/               # Только для default company (Vertex AR)

Key Dependencies
requirements.txt (backend):
fastapi==0.109.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
celery==5.3.6
redis==5.0.1
minio==7.2.3
httpx==0.26.0
pydantic==2.5.3
structlog==24.1.0

package.json (frontend):
react==18.3.1
@mui/material==5.15.15
react-router-dom==6.22.3
zustand==4.5.2
axios==1.6.8
qrcode.react==3.1.0

Database Schema Context
Primary Entities:
1. companies (multi-tenant isolation)
2. projects (folders within companies)
3. ar_content (portrait + NFT marker + videos)
4. videos (multiple per ar_content)
5. video_rotation_rules (scheduling logic)
6. ar_view_sessions (analytics)
7. storage_connections (MinIO/Yandex Disk)
8. notifications (email/telegram)

Key Relations:
Company 1:N Project N:M ARContent 1:N Video
Company 1:1 StorageConnection
ARContent 1:1 VideoRotationRule

Business Rules
1. Multi-tenant: каждый клиент = отдельное хранилище
2. AR Marker: Mind AR .mind files (image tracking)
3. Video Rotation: daily_cycle | date_specific | random_daily
4. Expiry: auto-deactivate content + notify 7 days before
5. QR Codes: auto-generated per ar_content.unique_id
6. Analytics: track FPS, device, location, session duration

Code Standards
Backend:
- Async/await everywhere (FastAPI native)
- Repository pattern for DB operations
- Pydantic v2 validation
- Dependency injection (Depends)
- Structured logging (structlog)
- Type hints 100%

Frontend:
- TypeScript strict mode
- React Hook Form + Zod
- Error Boundaries
- Suspense + lazy()
- MUI 5 + TailwindCSS

Environment Variables
Copy-paste полный .env:
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/vertex_ar
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
YANDEX_OAUTH_CLIENT_ID=abc123
YANDEX_OAUTH_CLIENT_SECRET=xyz789
ADMIN_EMAIL=admin@vertexar.com
TELEGRAM_BOT_TOKEN=123456:ABC
SECRET_KEY=your-super-secret-key-change-in-production



