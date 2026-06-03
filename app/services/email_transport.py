"""Shared SMTP transport helpers for application email sending."""

from __future__ import annotations

import smtplib
from email.message import Message


def send_smtp_message(
    message: Message,
    host: str,
    port: int,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 15,
    smtp_module=smtplib,
) -> None:
    """Send *message* via SMTP, preferring implicit SSL on port 465."""
    def _connect(factory, *args):
        try:
            return factory(*args, timeout=timeout)
        except TypeError:
            return factory(*args)

    if port == 465:
        with _connect(smtp_module.SMTP_SSL, host, port) as server:
            if username and password:
                server.login(username, password)
            server.send_message(message)
        return

    with _connect(smtp_module.SMTP, host, port) as server:
        server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(message)
