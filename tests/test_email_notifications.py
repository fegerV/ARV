"""
Integration tests for email notification system.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.services.email import EmailTemplate

client = TestClient(app)


@pytest.mark.asyncio
async def test_email_template_rendering():
    """Test that email templates can be rendered correctly."""
    # Import inside test to avoid issues with app context
    from app.services.email import render_email_template
    
    # Test rendering a simple template
    html_content, text_content = await render_email_template(
        EmailTemplate.NEW_COMPANY_CREATED,
        {
            "company_name": "Test Company",
            "admin_name": "Test Admin",
            "dashboard_url": "https://test.com/dashboard"
        }
    )
    
    assert "Test Company" in html_content
    assert "Test Admin" in html_content
    assert "https://test.com/dashboard" in html_content
    assert "Test Company" in text_content


@pytest.mark.asyncio
async def test_email_template_list():
    """Test that email templates can be listed."""
    from app.services.email import EmailTemplate
    
    templates = EmailTemplate.get_template_meta()
    
    # Check that we have the expected templates
    expected_templates = [
        EmailTemplate.NEW_COMPANY_CREATED,
        EmailTemplate.NEW_AR_CONTENT_CREATED,
        EmailTemplate.AR_CONTENT_READY,
        EmailTemplate.MARKER_GENERATION_COMPLETE,
        EmailTemplate.VIDEO_ROTATION_REMINDER
    ]
    
    for template_id in expected_templates:
        assert template_id in templates
        template = templates[template_id]
        assert "name" in template
        assert "description" in template
        assert "subject_example" in template
        assert "variables" in template


@patch("app.services.email.fm.send_message")
def test_send_email_endpoint(mock_send_message):
    """Test the send email notification endpoint."""
    # Mock the send_message method to avoid actually sending emails
    mock_send_message.return_value = None
    
    # Test data
    test_data = {
        "template_id": "NEW_COMPANY_CREATED",
        "recipients": ["test@example.com"],
        "data": {
            "company_name": "Test Company",
            "admin_name": "Test Admin",
            "dashboard_url": "https://test.com/dashboard"
        }
    }
    
    # Make request to the endpoint
    response = client.post("/api/notifications/email", json=test_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify that send_message was called
    mock_send_message.assert_called_once()


def test_list_email_templates_endpoint():
    """Test the list email templates endpoint."""
    response = client.get("/api/notifications/email/templates")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Check that we got template data
    assert isinstance(data, dict)
    assert len(data) > 0
    
    # Check that one of our expected templates is present
    assert "NEW_COMPANY_CREATED" in data
    template = data["NEW_COMPANY_CREATED"]
    assert "name" in template
    assert "description" in template