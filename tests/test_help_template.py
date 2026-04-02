from pathlib import Path


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
