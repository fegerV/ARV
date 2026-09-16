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
    assert '{{ t("settings.general") }}' in template

    assert 'action="/settings/general"' in general
    assert 'name="password_min_length"' in security
    assert 'name="thumbnail_quality"' in ar_tab
    assert 'name="default_content_lifetime_years"' in ar_tab
    assert 'name="video_processing_enabled"' in ar_tab
    assert 'x-ref="notificationsForm"' in notifications
    assert 'name="default_storage"' in storage
    assert 'action="/settings/backup"' in backup


def test_backup_tab_exposes_the_gfs_ladder_that_actually_governs():
    """The form must edit the rule rotation applies, not the dead legacy pair.

    Rotation uses the GFS ladder; ``backup_retention_days`` /
    ``backup_max_copies`` are ignored. Exposing only the legacy pair let an
    operator change retention settings that did nothing.
    """
    backup = Path("templates/partials/settings_backup_tab.html").read_text(encoding="utf-8")

    for field in (
        "backup_keep_daily",
        "backup_keep_weekly",
        "backup_keep_monthly",
        "backup_keep_yearly",
    ):
        assert f'name="{field}"' in backup
        assert f'type="number" name="{field}"' in backup

    # The legacy knobs survive only as hidden fields, so a save round-trips
    # whatever is stored without advertising them as effective.
    for legacy in ("backup_retention_days", "backup_max_copies"):
        assert f'type="hidden" name="{legacy}"' in backup
        assert f'type="number" name="{legacy}"' not in backup
