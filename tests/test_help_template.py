from pathlib import Path


def test_help_template_uses_initial_partials():
    template = Path("templates/help.html").read_text(encoding="utf-8")
    toc = Path("templates/help/partials/toc.html").read_text(encoding="utf-8")
    intro = Path("templates/help/partials/intro_section.html").read_text(encoding="utf-8")
    how_it_works = Path("templates/help/partials/how_it_works_section.html").read_text(encoding="utf-8")
    getting_started = Path("templates/help/partials/getting_started_section.html").read_text(encoding="utf-8")
    dashboard = Path("templates/help/partials/dashboard_section.html").read_text(encoding="utf-8")
    companies = Path("templates/help/partials/companies_section.html").read_text(encoding="utf-8")
    projects = Path("templates/help/partials/projects_section.html").read_text(encoding="utf-8")
    ar_content = Path("templates/help/partials/ar_content_section.html").read_text(encoding="utf-8")
    rotation = Path("templates/help/partials/rotation_section.html").read_text(encoding="utf-8")
    storage = Path("templates/help/partials/storage_section.html").read_text(encoding="utf-8")
    analytics = Path("templates/help/partials/analytics_section.html").read_text(encoding="utf-8")
    notifications = Path("templates/help/partials/notifications_section.html").read_text(encoding="utf-8")
    settings = Path("templates/help/partials/settings_section.html").read_text(encoding="utf-8")
    backups = Path("templates/help/partials/backups_section.html").read_text(encoding="utf-8")
    tips = Path("templates/help/partials/tips_section.html").read_text(encoding="utf-8")
    faq = Path("templates/help/partials/faq_section.html").read_text(encoding="utf-8")
    contacts = Path("templates/help/partials/contacts_section.html").read_text(encoding="utf-8")

    assert '{% include "help/partials/toc.html" %}' in template
    assert '{% include "help/partials/intro_section.html" %}' in template
    assert '{% include "help/partials/how_it_works_section.html" %}' in template
    assert '{% include "help/partials/getting_started_section.html" %}' in template
    assert '{% include "help/partials/dashboard_section.html" %}' in template
    assert '{% include "help/partials/companies_section.html" %}' in template
    assert '{% include "help/partials/projects_section.html" %}' in template
    assert '{% include "help/partials/ar_content_section.html" %}' in template
    assert '{% include "help/partials/rotation_section.html" %}' in template
    assert '{% include "help/partials/storage_section.html" %}' in template
    assert '{% include "help/partials/analytics_section.html" %}' in template
    assert '{% include "help/partials/notifications_section.html" %}' in template
    assert '{% include "help/partials/settings_section.html" %}' in template
    assert '{% include "help/partials/backups_section.html" %}' in template
    assert '{% include "help/partials/tips_section.html" %}' in template
    assert '{% include "help/partials/faq_section.html" %}' in template
    assert '{% include "help/partials/contacts_section.html" %}' in template

    assert 'href="#intro"' in toc
    assert 'id="intro"' in intro
    assert 'id="how-it-works"' in how_it_works
    assert 'id="getting-started"' in getting_started
    assert 'id="dashboard"' in dashboard
    assert 'id="companies"' in companies
    assert 'id="projects"' in projects
    assert 'id="ar-content"' in ar_content
    assert 'id="video-schedule-rotation"' in rotation
    assert 'id="storage"' in storage
    assert 'id="analytics"' in analytics
    assert 'id="notifications"' in notifications
    assert 'id="settings"' in settings
    assert 'id="backups"' in backups
    assert 'id="tips"' in tips
    assert 'id="faq"' in faq
    assert 'id="contacts"' in contacts
