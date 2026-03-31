from pathlib import Path


def test_settings_template_uses_partials_for_primary_tabs():
    template = Path("templates/settings.html").read_text(encoding="utf-8")
    general = Path("templates/partials/settings_general_tab.html").read_text(encoding="utf-8")
    security = Path("templates/partials/settings_security_tab.html").read_text(encoding="utf-8")
    ar_tab = Path("templates/partials/settings_ar_tab.html").read_text(encoding="utf-8")
    notifications = Path("templates/partials/settings_notifications_tab.html").read_text(encoding="utf-8")
    storage = Path("templates/partials/settings_storage_tab.html").read_text(encoding="utf-8")
    backup = Path("templates/partials/settings_backup_tab.html").read_text(encoding="utf-8")

    assert '{% include "partials/settings_general_tab.html" %}' in template
    assert '{% include "partials/settings_security_tab.html" %}' in template
    assert '{% include "partials/settings_ar_tab.html" %}' in template
    assert '{% include "partials/settings_notifications_tab.html" %}' in template
    assert '{% include "partials/settings_storage_tab.html" %}' in template
    assert '{% include "partials/settings_backup_tab.html" %}' in template

    assert 'action="/settings/general"' in general
    assert 'name="password_min_length"' in security
    assert 'name="thumbnail_quality"' in ar_tab
    assert 'x-ref="notificationsForm"' in notifications
    assert 'name="default_storage"' in storage
    assert 'action="/settings/backup"' in backup
