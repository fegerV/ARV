from pathlib import Path


def test_companies_list_template_uses_partials():
    template = Path("templates/companies/list.html").read_text(encoding="utf-8")
    header = Path("templates/companies/partials/list_header.html").read_text(encoding="utf-8")
    filters = Path("templates/companies/partials/list_filters.html").read_text(encoding="utf-8")
    table = Path("templates/companies/partials/list_table.html").read_text(encoding="utf-8")
    delete_modal = Path("templates/companies/partials/delete_modal.html").read_text(encoding="utf-8")

    assert '{% include "companies/partials/list_header.html" %}' in template
    assert '{% include "companies/partials/list_filters.html" %}' in template
    assert '{% include "companies/partials/list_table.html" %}' in template
    assert '{% include "companies/partials/delete_modal.html" %}' in template

    assert '{{ "Companies" if request.state.locale == "en" else "Компании" }}' in header
    assert 'id="status-filter"' in filters
    assert 'id="search-input"' in filters
    assert '{{ "No companies found" if request.state.locale == "en" else "Компании не найдены" }}' in table
    assert 'x-text="deleteCompany.name"' in delete_modal
