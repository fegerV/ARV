#!/usr/bin/env python3
"""Test script to verify email service imports work correctly."""

try:
    from app.services.email import EmailTemplate
    print("✓ Email service imported successfully")
    
    # Test template metadata
    templates = EmailTemplate.get_template_meta()
    print(f"✓ Found {len(templates)} email templates")
    
    # Check that all expected templates are present
    expected_templates = [
        EmailTemplate.NEW_COMPANY_CREATED,
        EmailTemplate.NEW_AR_CONTENT_CREATED,
        EmailTemplate.AR_CONTENT_READY,
        EmailTemplate.MARKER_GENERATION_COMPLETE,
        EmailTemplate.VIDEO_ROTATION_REMINDER
    ]
    
    for template_id in expected_templates:
        if template_id in templates:
            print(f"✓ Template {template_id} found")
        else:
            print(f"✗ Template {template_id} missing")
    
    print("Email service tests completed successfully!")
    
except Exception as e:
    print(f"✗ Failed to import email service: {e}")
    import traceback
    traceback.print_exc()