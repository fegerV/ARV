"""
Email service for sending notifications asynchronously.
Uses FastMail with SMTP transport and BackgroundTasks for async processing.
"""

from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import Dict, Any, List
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Configure email connection - only if settings are properly configured
if settings.MAIL_FROM and "@" in settings.MAIL_FROM:
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_STARTTLS=settings.MAIL_TLS,  # Изменено с MAIL_TLS на MAIL_STARTTLS
        MAIL_SSL_TLS=settings.MAIL_SSL,   # Изменено с MAIL_SSL на MAIL_SSL_TLS
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    fm = FastMail(conf)
else:
    # Email is not configured
    conf = None
    fm = None
    logger.warning("email_not_configured", mail_from=settings.MAIL_FROM)


class EmailTemplate:
    """Email template definitions"""
    
    NEW_COMPANY_CREATED = "NEW_COMPANY_CREATED"
    NEW_AR_CONTENT_CREATED = "NEW_AR_CONTENT_CREATED"
    AR_CONTENT_READY = "AR_CONTENT_READY"
    MARKER_GENERATION_COMPLETE = "MARKER_GENERATION_COMPLETE"
    VIDEO_ROTATION_REMINDER = "VIDEO_ROTATION_REMINDER"
    
    @classmethod
    def get_template_meta(cls) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all email templates"""
        return {
            cls.NEW_COMPANY_CREATED: {
                "name": "Новая компания создана",
                "description": "Отправляется при создании новой компании",
                "subject_example": "Новая компания {{company_name}} создана",
                "variables": ["company_name", "admin_name", "dashboard_url"]
            },
            cls.NEW_AR_CONTENT_CREATED: {
                "name": "Новый AR-контент создан",
                "description": "Отправляется при создании нового AR-контента",
                "subject_example": "Новый AR-контент: {{content_title}}",
                "variables": ["company_name", "project_name", "content_title", "content_url"]
            },
            cls.AR_CONTENT_READY: {
                "name": "AR-контент готов",
                "description": "Отправляется когда AR-контент полностью готов к использованию",
                "subject_example": "AR-контент {{content_title}} готов",
                "variables": ["company_name", "content_title", "content_url", "qr_code_url"]
            },
            cls.MARKER_GENERATION_COMPLETE: {
                "name": "Генерация маркера завершена",
                "description": "Отправляется когда генерация NFT маркера завершена",
                "subject_example": "Маркер для {{content_title}} готов",
                "variables": ["company_name", "content_title", "marker_url", "content_url"]
            },
            cls.VIDEO_ROTATION_REMINDER: {
                "name": "Напоминание о ротации видео",
                "description": "Отправляется перед автоматической ротацией видео",
                "subject_example": "Напоминание: ротация видео для {{content_title}}",
                "variables": ["company_name", "content_title", "next_rotation_date", "content_url"]
            }
        }


async def send_email(
    background_tasks: BackgroundTasks,
    subject: str,
    recipients: List[str],
    html_content: str,
    text_content: str = None
):
    """
    Send email asynchronously using background tasks.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        subject: Email subject
        recipients: List of recipient email addresses
        html_content: HTML email content
        text_content: Plain text email content (optional)
    """
    if fm is None:
        logger.warning("email_not_configured_skip_send", subject=subject, recipients=recipients)
        return
        
    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_content,
            subtype="html",
            text_body=text_content
        )
        
        # Add email sending to background tasks
        background_tasks.add_task(fm.send_message, message)
        
        logger.info(
            "email_queued",
            subject=subject,
            recipients=recipients,
            message_id=getattr(message, 'message_id', None)
        )
        
        return {"status": "queued", "recipients": recipients}
        
    except Exception as e:
        logger.error(
            "email_send_failed",
            subject=subject,
            recipients=recipients,
            error=str(e)
        )
        raise


async def render_email_template(template_id: str, data: Dict[str, Any]) -> tuple[str, str]:
    """
    Render email template with provided data.
    
    Args:
        template_id: Template identifier
        data: Template variables
        
    Returns:
        Tuple of (html_content, text_content)
    """
    # For now, we'll use simple string substitution
    # In a real implementation, this would use Jinja2 templates
    
    templates = {
        EmailTemplate.NEW_COMPANY_CREATED: {
            "subject": f"Новая компания {data.get('company_name', '')} создана",
            "html": f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <h2>Новая компания создана</h2>
                <p>Здравствуйте, {data.get('admin_name', 'Администратор')}!</p>
                <p>Компания <strong>{data.get('company_name', 'Не указано')}</strong> была успешно создана.</p>
                <p>Вы можете управлять компанией в <a href="{data.get('dashboard_url', '#')}">панели управления</a>.</p>
                <br>
                <p>С уважением,<br>Команда Vertex AR</p>
            </div>
            """,
            "text": f"""
            Новая компания создана
            
            Здравствуйте, {data.get('admin_name', 'Администратор')}!
            
            Компания {data.get('company_name', 'Не указано')} была успешно создана.
            
            Вы можете управлять компанией в панели управления: {data.get('dashboard_url', '#')}
            
            С уважением,
            Команда Vertex AR
            """
        },
        EmailTemplate.NEW_AR_CONTENT_CREATED: {
            "subject": f"Новый AR-контент: {data.get('content_title', '')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <h2>Новый AR-контент создан</h2>
                <p>Компания: <strong>{data.get('company_name', 'Не указано')}</strong></p>
                <p>Проект: <strong>{data.get('project_name', 'Не указано')}</strong></p>
                <p>Контент: <strong>{data.get('content_title', 'Не указано')}</strong></p>
                <p><a href="{data.get('content_url', '#')}">Просмотреть контент</a></p>
                <br>
                <p>С уважением,<br>Команда Vertex AR</p>
            </div>
            """,
            "text": f"""
            Новый AR-контент создан
            
            Компания: {data.get('company_name', 'Не указано')}
            Проект: {data.get('project_name', 'Не указано')}
            Контент: {data.get('content_title', 'Не указано')}
            
            Просмотреть контент: {data.get('content_url', '#')}
            
            С уважением,
            Команда Vertex AR
            """
        },
        EmailTemplate.AR_CONTENT_READY: {
            "subject": f"AR-контент {data.get('content_title', '')} готов",
            "html": f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <h2>AR-контент готов к использованию</h2>
                <p>Контент <strong>{data.get('content_title', 'Не указано')}</strong> полностью готов.</p>
                <p>Компания: {data.get('company_name', 'Не указано')}</p>
                <p><a href="{data.get('content_url', '#')}">Просмотреть контент</a></p>
                <p>QR-код: <a href="{data.get('qr_code_url', '#')}">Скачать QR-код</a></p>
                <br>
                <p>С уважением,<br>Команда Vertex AR</p>
            </div>
            """,
            "text": f"""
            AR-контент готов к использованию
            
            Контент {data.get('content_title', 'Не указано')} полностью готов.
            
            Компания: {data.get('company_name', 'Не указано')}
            
            Просмотреть контент: {data.get('content_url', '#')}
            QR-код: {data.get('qr_code_url', '#')}
            
            С уважением,
            Команда Vertex AR
            """
        },
        EmailTemplate.MARKER_GENERATION_COMPLETE: {
            "subject": f"Маркер для {data.get('content_title', '')} готов",
            "html": f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <h2>Генерация NFT маркера завершена</h2>
                <p>NFT маркер для контента <strong>{data.get('content_title', 'Не указано')}</strong> успешно сгенерирован.</p>
                <p>Компания: {data.get('company_name', 'Не указано')}</p>
                <p><a href="{data.get('marker_url', '#')}">Скачать маркер</a></p>
                <p><a href="{data.get('content_url', '#')}">Просмотреть контент</a></p>
                <br>
                <p>С уважением,<br>Команда Vertex AR</p>
            </div>
            """,
            "text": f"""
            Генерация NFT маркера завершена
            
            NFT маркер для контента {data.get('content_title', 'Не указано')} успешно сгенерирован.
            
            Компания: {data.get('company_name', 'Не указано')}
            
            Скачать маркер: {data.get('marker_url', '#')}
            Просмотреть контент: {data.get('content_url', '#')}
            
            С уважением,
            Команда Vertex AR
            """
        },
        EmailTemplate.VIDEO_ROTATION_REMINDER: {
            "subject": f"Напоминание: ротация видео для {data.get('content_title', '')}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <h2>Напоминание о ротации видео</h2>
                <p>Контент: <strong>{data.get('content_title', 'Не указано')}</strong></p>
                <p>Компания: {data.get('company_name', 'Не указано')}</p>
                <p>Следующая ротация запланирована на: {data.get('next_rotation_date', 'Не указано')}</p>
                <p><a href="{data.get('content_url', '#')}">Просмотреть контент</a></p>
                <br>
                <p>С уважением,<br>Команда Vertex AR</p>
            </div>
            """,
            "text": f"""
            Напоминание о ротации видео
            
            Контент: {data.get('content_title', 'Не указано')}
            
            Компания: {data.get('company_name', 'Не указано')}
            
            Следующая ротация запланирована на: {data.get('next_rotation_date', 'Не указано')}
            
            Просмотреть контент: {data.get('content_url', '#')}
            
            С уважением,
            Команда Vertex AR
            """
        }
    }
    
    template = templates.get(template_id)
    if not template:
        raise ValueError(f"Unknown template ID: {template_id}")
    
    # Simple variable substitution (in a real implementation, use Jinja2)
    html_content = template["html"]
    text_content = template["text"]
    
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        html_content = html_content.replace(placeholder, str(value))
        text_content = text_content.replace(placeholder, str(value))
    
    return html_content, text_content


async def send_template_email(
    background_tasks: BackgroundTasks,
    template_id: str,
    recipients: List[str],
    data: Dict[str, Any]
):
    """
    Send templated email asynchronously.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        template_id: Email template identifier
        recipients: List of recipient email addresses
        data: Template variables
    """
    # Render template
    subject_template = EmailTemplate.get_template_meta().get(template_id, {}).get("subject_example", "Уведомление Vertex AR")
    subject = subject_template
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
    
    html_content, text_content = await render_email_template(template_id, data)
    
    # Send email
    return await send_email(
        background_tasks=background_tasks,
        subject=subject,
        recipients=recipients,
        html_content=html_content,
        text_content=text_content
    )