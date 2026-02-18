#!/usr/bin/env python3
"""
Обновление боевого сервера ARV по SSH: git pull, зависимости, миграции, перезапуск, логи.

Использование:
  # С ключом (без пароля):
  python scripts/update_server.py

  # С паролем (нужен paramiko: pip install paramiko):
  set ARV_SSH_PASSWORD=ваш_пароль
  python scripts/update_server.py

Переменные окружения:
  ARV_SSH_HOST, ARV_SSH_USER  — хост и пользователь (по умолчанию 192.144.12.68, aruser)
  ARV_SSH_TARGET              — либо одна строка user@host
  ARV_SSH_PASSWORD            — пароль для входа (опционально, не хранить в репо)
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import paramiko

# Параметры по умолчанию
DEFAULT_HOST = "192.144.12.68"
DEFAULT_USER = "aruser"
SSH_TARGET_ENV = "ARV_SSH_TARGET"
SSH_PASSWORD_ENV = "ARV_SSH_PASSWORD"


def get_ssh_host_user() -> tuple[str, str]:
    """Возвращает (host, user)."""
    if target := os.environ.get(SSH_TARGET_ENV):
        if "@" in target:
            user, host = target.rsplit("@", 1)
            return host, user
    host = os.environ.get("ARV_SSH_HOST", DEFAULT_HOST)
    user = os.environ.get("ARV_SSH_USER", DEFAULT_USER)
    return host, user


def run_ssh_subprocess(command: str, target: str) -> int:
    """Выполняет команду через subprocess ssh (ключ)."""
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        target,
        command,
    ]
    return subprocess.call(cmd)


def run_ssh_paramiko(
    client: "paramiko.SSHClient",
    command: str,
) -> tuple[int, str, str]:
    """Выполняет команду через paramiko, возвращает (код, stdout, stderr)."""
    import paramiko
    stdin, stdout, stderr = client.exec_command(command)
    code = stdout.channel.recv_exit_status()
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    return code, out, err


def main_paramiko(host: str, user: str, password: str) -> int:
    """Обновление через paramiko (по паролю)."""
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=15,
        )
    except Exception as e:
        print(f"Ошибка подключения SSH: {e}", file=sys.stderr)
        return 1

    def run(cmd: str, desc: str = "") -> int:
        code, out, err = run_ssh_paramiko(client, cmd)
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        return code

    try:
        print(f"[ARV] Подключение к {user}@{host}...")
        print("\n[ARV] git pull...")
        if run("sudo -u arv bash -c 'cd /opt/arv/app && git pull'", "git pull") != 0:
            print("Ошибка: git pull не удался.", file=sys.stderr)
            return 1

        print("\n[ARV] pip install -r requirements.txt...")
        if run(
            "sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && pip install -r requirements.txt -q'",
            "pip",
        ) != 0:
            print("Ошибка: pip install не удался.", file=sys.stderr)
            return 2

        print("\n[ARV] alembic upgrade head...")
        if run(
            "sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'",
            "alembic",
        ) != 0:
            print("Ошибка: миграции не удались.", file=sys.stderr)
            return 3

        print("\n[ARV] systemctl restart arv...")
        if run("sudo systemctl restart arv", "restart") != 0:
            print("Ошибка: перезапуск не удался.", file=sys.stderr)
            return 4

        print("\n[ARV] Логи сервиса arv (последние 80 строк):\n")
        run("sudo journalctl -u arv -n 80 --no-pager", "journalctl")
        return 0
    finally:
        client.close()


def main_subprocess(host: str, user: str) -> int:
    """Обновление через subprocess ssh (по ключу)."""
    target = f"{user}@{host}"
    print(f"[ARV] Подключение к {target}...")

    steps = [
        ("git pull", "sudo -u arv bash -c 'cd /opt/arv/app && git pull'", 1),
        ("pip install", "sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && pip install -r requirements.txt -q'", 2),
        ("alembic upgrade head", "sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'", 3),
        ("systemctl restart arv", "sudo systemctl restart arv", 4),
    ]
    for desc, cmd, err_code in steps:
        print(f"\n[ARV] {desc}...")
        if run_ssh_subprocess(cmd, target) != 0:
            print(f"Ошибка: {desc} не удался.", file=sys.stderr)
            return err_code

    print("\n[ARV] Логи сервиса arv (последние 80 строк):\n")
    run_ssh_subprocess("sudo journalctl -u arv -n 80 --no-pager", target)
    return 0


def main() -> int:
    host, user = get_ssh_host_user()
    password = os.environ.get(SSH_PASSWORD_ENV)

    if password:
        try:
            import paramiko  # noqa: F401
        except ImportError:
            print("Для входа по паролю установите paramiko: pip install paramiko", file=sys.stderr)
            return 127
        return main_paramiko(host, user, password)
    return main_subprocess(host, user)


if __name__ == "__main__":
    sys.exit(main())
