---
trigger: always_on
alwaysApply: true
---
**Project: Vertex AR B2B Platform**
FastAPI 0.109 + PostgreSQL 15 + React 18 + Mind AR 1.2.5

ARCHITECTURE:
Backend: FastAPI async → SQLAlchemy 2.0 async → PostgreSQL 15 (PITR)
Frontend: React 18 + TypeScript + MUI 5 + TailwindCSS + Vite
AR Engine: Mind AR image tracking + Three.js video texture
Storage: Multi-tenant (Local/MinIO/Yandex Disk OAuth)
Queue: Celery 5.3 + Redis 7 (marker generation)
Monitoring: Prometheus + Grafana + Telegram alerts

CORE ENTITIES:
Company (multi-tenant) → Project (folder) → ARContent (portrait+NFT+video)
VideoRotationRule (daily/date/random scheduling)
ARViewSession (device/FPS/location analytics)

BUSINESS FLOW:
1. Admin creates Company → Storage Connection (Yandex Disk)
2. Create Project → Upload portrait → Generate MindAR marker
3. Upload videos → Set rotation rules (daily/seasonal)
4. Generate QR code → Client prints → Users scan → AR plays

CRITICAL RULES:
- Multi-tenant isolation (separate storage per company)
- Video rotation: date_specific > daily_cycle > default_video
- Auto-expiry + notifications 7 days before
- NFT markers: mind-ar-js-compiler → .mind files
- Analytics: track FPS, device detection, geo

FILE STRUCTURE:
app/
├── main.py (FastAPI lifespan)
├── core/ (config, db, security)
├── models/ (Company, Project, ARContent)
├── schemas/ (Pydantic v2)
├── api/routes/ (companies.py, ar_content.py)
├── services/ (storage/, video_scheduler.py)
└── tasks/ (celery marker generation)

TECH CONSTRAINTS:
- Async-first (FastAPI native async/await)
- Repository pattern + SQLAlchemy 2.0 selectinload
- Docker Compose V2 (service names in DATABASE_URL)
- Windows dev → WSL2 + Docker → Ubuntu prod parity
- 100% TypeScript + Python type hints

Auto-import preferences:
- FastAPI: APIRouter, Depends, HTTPException
- SQLAlchemy: select, AsyncSession, relationship
- React: useState, useEffect, useCallback
- MUI: Box, Button, Typography

Suggested patterns:
Backend: async def endpoint(db: AsyncSession = Depends(get_db))
Frontend: const [state, setState] = useState<Type>(initial)

Testing framework: pytest + pytest-asyncio + Playwright
