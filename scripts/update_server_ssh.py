#!/usr/bin/env python3
"""
Обновление приложения на сервере по SSH и просмотр логов.

Использование:
    set ARV_SSH_PASSWORD=...
    python scripts/update_server_ssh.py           # обновить код
    python scripts/update_server_ssh.py --logs   # только показать логи arv
    python scripts/update_server_ssh.py --restart # обновить и перезапустить (нужен sudo)

Пароль из переменной окружения ARV_SSH_PASSWORD.
Опционально: ARV_SSH_HOST (по умолчанию 192.144.12.68), ARV_SSH_USER (aruser).
"""
from __future__ import annotations

import os
import sys

try:
    import paramiko
except ImportError:
    print("Установите paramiko: pip install paramiko", file=sys.stderr)
    sys.exit(1)

SSH_HOST = os.environ.get("ARV_SSH_HOST", "192.144.12.68")
SSH_USER = os.environ.get("ARV_SSH_USER", "aruser")
SSH_PASSWORD = os.environ.get("ARV_SSH_PASSWORD")
APP_DIR = "/opt/arv/app"
VENV_DIR = "/opt/arv/venv"


def run_cmd(client: paramiko.SSHClient, cmd: str, allow_fail: bool = False) -> int:
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=False)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return exit_code


def run_ssh_commands(do_update: bool = True, do_logs: bool = False, do_restart: bool = False) -> None:
    if not SSH_PASSWORD:
        print("Задайте пароль: set ARV_SSH_PASSWORD=... (Windows) или export ARV_SSH_PASSWORD=... (Linux)", file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=SSH_HOST,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
    except Exception as e:
        print(f"Ошибка подключения к {SSH_HOST}: {e}", file=sys.stderr)
        sys.exit(1)

    if do_update:
        pw_esc = SSH_PASSWORD.replace("'", "'\"'\"'")
        # Команды от имени пользователя arv (владелец /opt/arv/app)
        commands = [
            f"echo '{pw_esc}' | sudo -S -u arv bash -c 'cd {APP_DIR} && git fetch origin && git reset --hard origin/main'",
            f"echo '{pw_esc}' | sudo -S -u arv bash -c 'cd {APP_DIR} && {VENV_DIR}/bin/pip install -r requirements.txt -q'",
            f"echo '{pw_esc}' | sudo -S -u arv bash -c 'cd {APP_DIR} && PYTHONPATH={APP_DIR} {VENV_DIR}/bin/alembic upgrade head'",
            f"echo '{pw_esc}' | sudo -S -u arv bash -c 'cd {APP_DIR} && (command -v npm >/dev/null 2>&1 && npm ci && npm run build:css || true)'",
        ]
        for cmd in commands:
            print(f"Выполняю: ... (git/pip/alembic/npm)...")
            code = run_cmd(client, cmd)
            if code != 0 and "npm" not in cmd:
                client.close()
                sys.exit(code)
        print("Код обновлён.")

    if do_restart:
        print("Перезапуск arv...")
        pw_esc = SSH_PASSWORD.replace("'", "'\"'\"'")
        run_cmd(client, f"echo '{pw_esc}' | sudo -S systemctl restart arv 2>/dev/null || true")

    if do_logs:
        print("\n--- Логи приложения arv (последние 80 строк) ---\n")
        code = run_cmd(client, "journalctl -u arv -n 80 --no-pager -o short-iso 2>/dev/null")
        if code != 0:
            pw_esc = SSH_PASSWORD.replace("'", "'\"'\"'")
            run_cmd(client, f"echo '{pw_esc}' | sudo -S journalctl -u arv -n 80 --no-pager -o short-iso")

    client.close()
    if do_update and not do_restart:
        print("\nПерезапустите приложение на сервере: sudo systemctl restart arv")


if __name__ == "__main__":
    do_logs = "--logs" in sys.argv
    do_restart = "--restart" in sys.argv
    do_update = True  # всегда обновлять при запуске; с --logs дополнительно показываем логи
    run_ssh_commands(do_update=do_update, do_logs=do_logs, do_restart=do_restart)
