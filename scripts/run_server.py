"""
Запуск uvicorn с учётом .env: SSL включается автоматически, если заданы SSL_KEYFILE и SSL_CERTFILE.

Использование (из корня проекта):
  python scripts/run_server.py

Для работы https://ar.neuroimagen.ru/view/... при пробросе 443→8000 сервер должен слушать
порт 8000 по HTTPS (TLS). При запуске через «python -m uvicorn app.main:app» SSL из .env
не подставляется — используйте этот скрипт или «python -m app.main».
"""
import sys
from pathlib import Path

# Корень проекта = родительская папка scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main() -> None:
    import uvicorn
    from app.core.config import settings

    run_kw: dict = {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
    }
    if settings.ssl_enabled:
        run_kw["ssl_keyfile"] = settings.SSL_KEYFILE
        run_kw["ssl_certfile"] = settings.SSL_CERTFILE
        print("SSL enabled: HTTPS on port 8000 (use with 443->8000 port forward)")
    else:
        print("SSL disabled: HTTP only. Set SSL_KEYFILE and SSL_CERTFILE in .env for HTTPS.")

    uvicorn.run("app.main:app", **run_kw)


if __name__ == "__main__":
    main()
