"""Shared SMTP transport helpers for application email sending."""

from __future__ import annotations

import logging
import smtplib
from email.message import Message
from pathlib import Path
from typing import Dict, List, Optional, Union

from app.core.config import get_settings

logger = logging.getLogger(__name__)


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


def _render_template(template_name: str, context: Dict) -> Optional[str]:
    """Render an email template from the templates directory.

    Falls back to the ``message`` key in *context* if the template
    file is not found, so callers always get a usable body.
    """
    from email.mime.text import MIMEText
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _settings = get_settings()
    template_dirs = [
        Path("templates"),
        Path(_settings.TEMPLATES_DIR),
    ]
    for tpl_dir in template_dirs:
        candidate = tpl_dir / template_name
        if candidate.exists():
            env = Environment(
                loader=FileSystemLoader(str(tpl_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            template = env.get_template(template_name)
            return template.render(**context)

    message = context.get("message", "")
    if isinstance(message, (str, MIMEText)):
        return str(message)
    return None


def send_email(
    to_email: Union[str, List[str]],
    subject: str,
    template_name: str,
    context: Optional[Dict] = None,
    **kwargs,
) -> None:
    """Send an email via SMTP using a Jinja2 template or plain-text fallback.

    Args:
        to_email: Recipient address or list of addresses.
        subject: Email subject line.
        template_name: Name of the Jinja2 template file inside ``templates/``.
        context: Variables passed to the template renderer.
        **kwargs: Additional keyword arguments (currently ignored — reserved
            for future extensibility such as attachments).
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    settings_inst = get_settings()
    if context is None:
        context = {}

    recipients = [to_email] if isinstance(to_email, str) else list(to_email)
    if not recipients:
        raise ValueError("send_email requires at least one recipient")

    rendered = _render_template(template_name, context)
    html_body = rendered if rendered is not None else context.get("message", "")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings_inst.SMTP_FROM_EMAIL
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html" if "<" in html_body else "plain", "utf-8"))

    send_smtp_message(
        msg,
        settings_inst.SMTP_HOST,
        settings_inst.SMTP_PORT,
        settings_inst.SMTP_USERNAME or None,
        settings_inst.SMTP_PASSWORD or None,
        smtp_module=smtplib,
    )
    logger.info("email_sent", recipients=len(recipients), subject=subject)
