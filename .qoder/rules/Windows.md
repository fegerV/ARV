---
trigger: always_on
alwaysApply: true
---
1. 🚨 File Paths & Separators
text
❌ Windows: C:\project\storage\content\file.jpg
❌ Windows: file\path\to\video.mp4

✅ Cross-platform:
pathlib.Path("storage/content/file.jpg")
os.path.join("storage", "content", "file.jpg")
"/storage/content/file.jpg"  # абсолютные пути одинаковы
Правила:

python
# ✅ Используй pathlib (Python 3.9+)
from pathlib import Path
content_dir = Path("storage") / "content" / "videos"
video_path = content_dir / "video.mp4"

# ✅ В .env абсолютные пути от корня проекта
STORAGE_CONTENT_PATH=/app/storage/content

# ✅ Docker volumes монтируй одинаково
volumes:
  - ./storage/content:/app/storage/content  # одинаковый путь внутри контейнера
2. 🔢 Line Endings (CRLF vs LF)
text
❌ Windows: CRLF (\r\n)
✅ Linux:  LF (\n)

Проблемы:
- Git diff покажет все файлы измененными
- Docker COPY сломает скрипты
- Cron jobs не запустятся
Решение:

bash
# .gitattributes (в корне проекта)
# Автоматическая конвертация в LF для всех файлов
* text=auto eol=lf
*.py text eol=lf
*.sh text eol=lf
*.sql text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.html text eol=lf
*.css text eol=lf
*.js text eol=lf
*.ts text eol=lf
VS Code settings.json:

json
{
  "files.eol": "\n",
  "files.encoding": "utf8",
  "[python]": { "editor.insertSpaces": true, "editor.tabSize": 4 },
  "[yaml]": { "editor.insertSpaces": true, "editor.tabSize": 2 }
}
3. 🐚 Shell Scripts (CMD vs Bash)
text
❌ Windows CMD:
docker-compose up

✅ Linux Bash:
docker-compose up -d

❌ ifconfig / ipconfig
❌ dir / ls -la
❌ type / cat file.txt
Решение:

bash
#!/bin/bash  # ← Обязательно!
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Кросс-платформенные команды
docker compose up -d  # Docker Compose V2
curl -f -sSL https://example.com  # fail on HTTP error
find . -name "*.py" -print0 | xargs -0 black  # safe paths
Windows WSL2 (рекомендуется):

bash
# Установи WSL2 + Ubuntu
wsl --install -d Ubuntu
# Разработка в WSL = идентично Linux серверу
code .  # VS Code подключается к WSL
4. 📦 Python Dependencies & Virtualenv
text
❌ Windows: pip.exe, Scripts\
✅ Linux:  pip, bin/

Проблемы:
pip install psycopg2-binary  # Скомпилируется по-разному
Решение:

bash
# requirements.txt с pinned версиями
fastapi==0.109.0
sqlalchemy[asyncio]==2.0.25
psycopg2-binary==2.9.9  # pre-compiled wheels

# docker/Dockerfile использует Linux wheels
FROM python:3.11-slim
RUN pip install --no-cache-dir -r requirements.txt

# poetry.lock для точной воспроизводимости
poetry export -f requirements.txt --without-hashes > requirements.txt
5. 🐳 Docker: Единственная точка истины
text
✅ Docker = Production parity
Windows dev → Docker → Ubuntu prod = ✅ идентично

docker-compose.yml:
version: '3.8'
services:
  app:
    build: .          # Собирается одинаково
    volumes:
      - ./storage:/app/storage  # Host paths НЕ используются в prod!
docker-compose.override.yml (только для разработки):

text
services:
  app:
    volumes:
      - .:/app          # Hot reload только в dev
      - ./storage:/app/storage
    ports:
      - "8000:8000"     # Только в dev
    environment:
      - DEBUG=true
6. ⚙️ File Permissions & Ownership
text
❌ Windows: Everyone RW
✅ Linux:  755 (dirs), 644 (files), uid:gid=1000:1000

Проблемы:
- Docker не может писать в storage/
- Cron jobs от root
Решение:

text
# Dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
WORKDIR /app

# docker-compose.yml
user: "1000:1000"  # uid:gid
volumes:
  - ./storage:/app/storage  # owner:group на хосте должен совпадать
Windows → Linux sync:

bash
# На Windows (WSL или Git Bash)
sudo chown -R 1000:1000 storage/
sudo chmod -R 755 storage/
find storage/ -type f -exec chmod 644 {} \;
7. 🌐 Networking & Ports
text
❌ Windows: localhost:5432
✅ Linux:  postgres:5432 (Docker networking)

Проблемы:
- DATABASE_URL=postgresql://localhost:5432/ не работает в Docker
Правильная конфигурация:

text
# .env (development)
DATABASE_URL=postgresql+asyncpg://vertex_ar:password@localhost:5432/vertex_ar
REDIS_URL=redis://localhost:6379/0

# docker-compose.yml (production-like)
DATABASE_URL=postgresql+asyncpg://vertex_ar:password@postgres:5432/vertex_ar
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
8. 📁 Volume Mounts & Paths
text
❌ Windows: C:\Users\user\project\storage
✅ Docker:  /app/storage (внутри контейнера)

Проблемы:
- Относительные пути ломаются
- Windows paths с пробелами
Правильная структура:

text
project/
├── docker-compose.yml
├── .env                    # DATABASE_URL=postgresql://postgres:5432/...
├── app/                    # Python код
├── storage/                # Только dev mount!
├── frontend/               # React build
└── nginx.conf
text
# docker-compose.yml
services:
  app:
    volumes:
      - ./storage/content:/app/storage/content  # Только для Vertex AR local
      # НЕ монтируем код в prod!
  nginx:
    volumes:
      - ./frontend/dist:/usr/share/nginx/html  # Статические файлы
9. 🐳 Docker Build Context
text
❌ Windows: длинные пути >260 символов
✅ Docker: короткие пути, .dockerignore

.dockerignore:
node_modules/
.git/
__pycache__/
*.pyc
.env
storage/
!.env.example
!storage/content/  # Только для local dev
10. IDE Settings (VS Code)
.vscode/settings.json:

json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "docker.showStartWarning": false,
  "files.eol": "\n",
  "files.trimTrailingWhitespace": true,
  "search.exclude": {
    "**/node_modules": true,
    "**/storage": true,
    "**/__pycache__": true
  },
  "docker-compose.filesToInclude": ["docker-compose.yml", "docker-compose.override.yml"]
}
Extensions:

text
- Python (Microsoft)
- Docker (Microsoft) 
- Remote - WSL (Microsoft)
- GitLens
- Prettier
- Black Formatter
11. WSL2 (Рекомендуется для Windows)
text
1. wsl --install -d Ubuntu
2. В WSL: git clone project
3. code .  # VS Code подключается к WSL
4. docker-compose up -d  # Идентично Linux

Преимущества WSL2:
✅ Docker работает нативно (не Docker Desktop)
✅ File permissions правильные
✅ Shell = bash
✅ Python wheels для Linux
✅ Нет CRLF проблем
12. Production Checklist
bash
#!/bin/bash
# pre-deploy-check.sh
echo "🔍 Production readiness check..."

# 1. Line endings
git ls-files | xargs file | grep CRLF && echo "❌ CRLF detected!" || echo "✅ LF OK"

# 2. Docker build test
docker-compose build --no-cache app || exit 1

# 3. Health check
docker-compose up -d postgres redis app
sleep 30
curl -f http://localhost:8000/api/health/status || exit 1

# 4. Permissions
sudo chown -R 1000:1000 storage/
sudo chmod -R 755 storage/

echo "✅ Ready for production!"
13. Quick Setup Script (Windows → Linux)
powershell
# setup-windows-dev.ps1
# 1. Установить WSL2
wsl --install -d Ubuntu

# 2. В WSL
wsl
git clone <repo>
cd vertex-ar
cp .env.example .env
sudo chown -R $USER:$USER storage/
docker-compose up -d

# 3. VS Code
code .
# F1 → "Remote-WSL: Reopen in WSL"
🎯 Ключевые правила:
text
1. ✅ Docker = Single Source of Truth
2. ✅ WSL2 для Windows dev (или Git Bash + Docker Desktop)
3. ✅ pathlib.Path() вместо строковых путей
4. ✅ .gitattributes для LF endings
5. ✅ docker-compose.override.yml только для dev
6. ✅ user: "1000:1000" в Docker
7. ✅ DATABASE_URL с Docker service names
8. ✅ pre-commit hooks + CI checks
Результат: Код написан на Windows → работает идентично на Ubuntu server! 🚀