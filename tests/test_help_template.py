from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader


def _render_backups_section(is_super_admin: bool) -> str:
    """Render the backup partial on its own, with no application imports.

    The partial only needs ``request.state.locale`` and the role flag, so it can
    be exercised without booting the app (and therefore without a database).
    """
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("help/partials/backups_section.html")
    return template.render(
        request=SimpleNamespace(state=SimpleNamespace(locale="ru")),
        is_super_admin=is_super_admin,
    )


def test_help_template_uses_clean_partials():
    template = Path("templates/help.html").read_text(encoding="utf-8")
    toc = Path("templates/help/partials/toc.html").read_text(encoding="utf-8")
    how_it_works = Path("templates/help/partials/how_it_works_section.html").read_text(encoding="utf-8")
    getting_started = Path("templates/help/partials/getting_started_section.html").read_text(encoding="utf-8")
    storage = Path("templates/help/partials/storage_section.html").read_text(encoding="utf-8")

    assert '{% include "help/partials/toc.html" %}' in template
    assert '{{ "Contents" if is_en else "Содержание" }}' in toc
    assert '{{ "How the platform works" if is_en else "Как работает платформа" }}' in how_it_works
    assert '{{ "Getting started" if is_en else "С чего начать" }}' in getting_started
    assert '{{ "Storage" if is_en else "Хранение" }}' in storage


def test_help_backup_guide_covers_create_and_restore():
    """The backup section must actually document both halves of the job."""
    rendered = _render_backups_section(is_super_admin=True)

    for heading in (
        "Что попадает в копии",
        "Автоматическое создание",
        "Создание копии вручную",
        "Проверка, что копия пригодна",
        "Восстановление из копии",
        "Важные детали",
    ):
        assert heading in rendered, f"backup guide lost its section: {heading}"


def test_help_backup_guide_hides_the_operator_procedure_from_tenants():
    """Host paths and CLI commands are for the operator, not for every tenant.

    /backups and the settings tab are super-admin only, so a tenant reading the
    help page must not be handed the runbook either.
    """
    tenant = _render_backups_section(is_super_admin=False)
    admin = _render_backups_section(is_super_admin=True)

    for operator_only in ("app.cli.backup", "--from-file", "/opt/arv/venv", "vertex_ar_recovered"):
        assert operator_only in admin, f"admin lost the operator step: {operator_only}"
        assert operator_only not in tenant, f"tenant can see the operator step: {operator_only}"

    assert "обратитесь к администратору" in tenant
