from pathlib import Path


def test_notifications_template_uses_partials():
    template = Path("templates/notifications.html").read_text(encoding="utf-8")
    header = Path("templates/notifications/partials/list_header.html").read_text(encoding="utf-8")
    table = Path("templates/notifications/partials/list_table.html").read_text(encoding="utf-8")
    pagination = Path("templates/notifications/partials/pagination.html").read_text(encoding="utf-8")
    delete_modal = Path("templates/notifications/partials/delete_modal.html").read_text(encoding="utf-8")

    assert '{% include "notifications/partials/list_header.html" %}' in template
    assert '{% include "notifications/partials/list_table.html" %}' in template
    assert '{% include "notifications/partials/pagination.html" %}' in template
    assert '{% include "notifications/partials/delete_modal.html" %}' in template

    assert "Track system events and status updates" in header
    assert "No notifications" in table
    assert 'Page <span class="font-semibold">{{ page }}</span>' in pagination
    assert "Delete Notification" in delete_modal
