from pathlib import Path


def test_projects_form_template_uses_partials():
    template = Path("templates/projects/form.html").read_text(encoding="utf-8")
    header = Path("templates/projects/partials/form_header.html").read_text(encoding="utf-8")
    error_alert = Path("templates/projects/partials/form_error_alert.html").read_text(encoding="utf-8")
    fields = Path("templates/projects/partials/form_fields.html").read_text(encoding="utf-8")
    actions = Path("templates/projects/partials/form_actions.html").read_text(encoding="utf-8")
    info_card = Path("templates/projects/partials/form_info_card.html").read_text(encoding="utf-8")

    assert '{% include "projects/partials/form_header.html" %}' in template
    assert '{% include "projects/partials/form_error_alert.html" %}' in template
    assert '{% include "projects/partials/form_fields.html" %}' in template
    assert '{% include "projects/partials/form_actions.html" %}' in template
    assert '{% include "projects/partials/form_info_card.html" %}' in template

    assert "Create New Project" in header
    assert "Error" in error_alert
    assert 'id="company_id"' in fields
    assert "Back to Projects" in actions
    assert "Projects organize your AR content" in info_card
