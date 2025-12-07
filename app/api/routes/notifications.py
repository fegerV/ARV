"""
Notification API routes for email notifications.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import structlog

from app.services.email import send_template_email, EmailTemplate
from app.core.errors import AppException

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = structlog.get_logger()


class EmailNotificationRequest(BaseModel):
    """Request model for sending email notifications."""
    template_id: str
    recipients: List[str]
    data: Dict[str, Any]


class EmailNotificationResponse(BaseModel):
    """Response model for email notification."""
    status: str
    message: str


@router.post("/email", response_model=EmailNotificationResponse)
async def send_email_notification(
    request: EmailNotificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Send email notification using template.
    
    This endpoint allows sending templated emails by specifying a template ID
    and providing the required data for that template.
    """
    try:
        # Validate template ID
        template_meta = EmailTemplate.get_template_meta()
        if request.template_id not in template_meta:
            raise AppException(
                status_code=400,
                detail=f"Unknown template ID: {request.template_id}",
                code="INVALID_TEMPLATE_ID"
            )
        
        # Validate recipients
        if not request.recipients:
            raise AppException(
                status_code=400,
                detail="At least one recipient is required",
                code="MISSING_RECIPIENTS"
            )
        
        # Send email using template
        await send_template_email(
            background_tasks=background_tasks,
            template_id=request.template_id,
            recipients=request.recipients,
            data=request.data
        )
        
        logger.info(
            "email_notification_sent",
            template_id=request.template_id,
            recipients=request.recipients
        )
        
        return EmailNotificationResponse(
            status="success",
            message=f"Email queued for delivery to {len(request.recipients)} recipients"
        )
        
    except AppException:
        # Re-raise AppExceptions
        raise
    except Exception as e:
        logger.error(
            "email_notification_failed",
            template_id=request.template_id,
            recipients=request.recipients,
            error=str(e)
        )
        raise AppException(
            status_code=500,
            detail="Failed to send email notification",
            code="EMAIL_SEND_FAILED",
            meta={"error": str(e)}
        )


@router.get("/email/templates")
async def list_email_templates():
    """
    List available email templates.
    
    Returns metadata about all available email templates including
    required variables and examples.
    """
    templates = EmailTemplate.get_template_meta()
    return templates