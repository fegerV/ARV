# Email Notification System Setup Guide

## Overview

This guide explains how to set up and use the email notification system in the Vertex AR B2B Platform.

## Prerequisites

1. SMTP server credentials (Postmark, Mailgun, Yandex, Gmail, etc.)
2. Environment variables configured in `.env` file

## Configuration

Add the following environment variables to your `.env` file:

```env
# Email Configuration
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_password
MAIL_FROM=noreply@yourdomain.com
MAIL_FROM_NAME="Vertex AR Platform"
MAIL_SERVER=smtp.yandex.ru  # or smtp.gmail.com, smtp.mailgun.org, etc.
MAIL_PORT=465  # or 587 for TLS
MAIL_TLS=False  # or True if using TLS
MAIL_SSL=True   # or False if using TLS
```

## Available Email Templates

The system comes with 5 built-in email templates:

1. **NEW_COMPANY_CREATED** - Sent when a new company is created
2. **NEW_AR_CONTENT_CREATED** - Sent when new AR content is created
3. **AR_CONTENT_READY** - Sent when AR content is fully ready
4. **MARKER_GENERATION_COMPLETE** - Sent when NFT marker generation completes
5. **VIDEO_ROTATION_REMINDER** - Sent as a reminder before video rotation

## Using Email Notifications

### Backend Usage

To send an email notification from backend code:

```python
from fastapi import BackgroundTasks
from app.services.email import send_template_email, EmailTemplate

async def some_function(background_tasks: BackgroundTasks):
    await send_template_email(
        background_tasks=background_tasks,
        template_id=EmailTemplate.NEW_COMPANY_CREATED,
        recipients=["user@example.com"],
        data={
            "company_name": "Test Company",
            "admin_name": "Admin User",
            "dashboard_url": "https://admin.vertexar.com/dashboard"
        }
    )
```

### API Usage

Send email notifications via the API:

```bash
curl -X POST "http://localhost:8000/api/notifications/email" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "NEW_COMPANY_CREATED",
    "recipients": ["user@example.com"],
    "data": {
      "company_name": "Test Company",
      "admin_name": "Admin User",
      "dashboard_url": "https://admin.vertexar.com/dashboard"
    }
  }'
```

### Frontend Usage

From the frontend, use the email service:

```typescript
import { emailService } from '@/services/emailService';

// Send email notification
await emailService.sendEmail({
  template_id: 'NEW_COMPANY_CREATED',
  recipients: ['user@example.com'],
  data: {
    company_name: 'Test Company',
    admin_name: 'Admin User',
    dashboard_url: 'https://admin.vertexar.com/dashboard'
  }
});
```

## Admin Interface

The email templates can be viewed and previewed in the admin interface:

1. Navigate to Settings → Email Templates
2. Select a template from the list
3. View template details and preview with sample data

## Testing

Run the email notification tests:

```bash
pytest tests/test_email_notifications.py
```

## Troubleshooting

### Common Issues

1. **SMTP Authentication Failed** - Check your credentials in the `.env` file
2. **Connection Timeout** - Verify SMTP server settings (server, port, TLS/SSL)
3. **Email Not Received** - Check spam/junk folders

### Logs

Check application logs for email-related messages:
- `email_queued` - Email added to background tasks
- `email_send_failed` - Email sending failed
- `company_creation_email_sent` - Company creation email sent
- `company_creation_email_failed` - Company creation email failed

### Debugging

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your `.env` file.