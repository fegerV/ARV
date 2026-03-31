from pathlib import Path


def test_ar_content_form_template_uses_initial_partials():
    template = Path("templates/ar-content/form.html").read_text(encoding="utf-8")
    header = Path("templates/ar-content/partials/form_header.html").read_text(encoding="utf-8")
    company_project = Path("templates/ar-content/partials/form_company_project_section.html").read_text(encoding="utf-8")
    customer = Path("templates/ar-content/partials/form_customer_section.html").read_text(encoding="utf-8")
    file_upload = Path("templates/ar-content/partials/form_file_upload_section.html").read_text(encoding="utf-8")
    status = Path("templates/ar-content/partials/form_status_section.html").read_text(encoding="utf-8")
    actions = Path("templates/ar-content/partials/form_actions_section.html").read_text(encoding="utf-8")

    assert '{% include "ar-content/partials/form_header.html" %}' in template
    assert '{% include "ar-content/partials/form_company_project_section.html" %}' in template
    assert '{% include "ar-content/partials/form_customer_section.html" %}' in template
    assert '{% include "ar-content/partials/form_file_upload_section.html" %}' in template
    assert '{% include "ar-content/partials/form_status_section.html" %}' in template
    assert '{% include "ar-content/partials/form_actions_section.html" %}' in template

    assert "arrow_back" in header
    assert 'id="company_id"' in company_project
    assert 'id="customer_name"' in customer
    assert 'id="photo_file"' in file_upload
    assert 'id="video_file"' in file_upload
    assert 'id="status"' in status
    assert "submitPhase" in actions
