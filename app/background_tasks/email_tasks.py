"""
Email-related background tasks.
"""

import logging
from typing import Dict, List, Optional, Union
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.email_service import send_email as _send_email
from . import run_background_task

logger = logging.getLogger(__name__)


async def send_email(
    background_tasks: BackgroundTasks,
    to_email: Union[str, List[str]],
    subject: str,
    template_name: str,
    context: Dict = None,
    **kwargs
) -> None:
    """
    Send an email in the background.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        to_email: Email address or list of email addresses to send to
        subject: Email subject
        template_name: Name of the email template to use
        context: Context variables for the email template
        **kwargs: Additional arguments to pass to the email service
    """
    if context is None:
        context = {}
    
    await run_background_task(
        background_tasks,
        _send_email,
        to_email=to_email,
        subject=subject,
        template_name=template_name,
        context=context,
        **kwargs
    )
    logger.info("email_task_queued", to_email=to_email, subject=subject)


async def send_admin_notification(
    background_tasks: BackgroundTasks,
    subject: str,
    message: str,
    context: Optional[Dict] = None
) -> None:
    """
    Send a notification to the admin email.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        subject: Email subject
        message: Notification message
        context: Additional context for the email template
    """
    if context is None:
        context = {}
    
    context.setdefault("message", message)
    
    await send_email(
        background_tasks=background_tasks,
        to_email=settings.ADMIN_EMAIL,
        subject=f"[Vertex AR] {subject}",
        template_name="admin_notification.html",
        context=context
    )
