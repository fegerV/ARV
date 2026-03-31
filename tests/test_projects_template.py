from pathlib import Path


def test_projects_list_template_uses_partials():
    template = Path("templates/projects/list.html").read_text(encoding="utf-8")
    header = Path("templates/projects/partials/list_header.html").read_text(encoding="utf-8")
    filters = Path("templates/projects/partials/list_filters.html").read_text(encoding="utf-8")
    table = Path("templates/projects/partials/list_table.html").read_text(encoding="utf-8")
    delete_modal = Path("templates/projects/partials/delete_modal.html").read_text(encoding="utf-8")

    assert '{% include "projects/partials/list_header.html" %}' in template
    assert '{% include "projects/partials/list_filters.html" %}' in template
    assert '{% include "projects/partials/list_table.html" %}' in template
    assert '{% include "projects/partials/delete_modal.html" %}' in template

    assert "Manage and organize your AR projects" in header
    assert 'id="status-filter"' in filters
    assert 'id="company-filter"' in filters
    assert "No projects found" in table
    assert 'x-text="deleteProject.name"' in delete_modal
