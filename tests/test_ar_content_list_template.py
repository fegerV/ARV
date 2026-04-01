from pathlib import Path


def test_ar_content_list_template_uses_i18n_labels():
    template = Path("templates/ar-content/list.html").read_text(encoding="utf-8")

    assert '{{ t("ar_content.title") }}' in template
    assert '{{ t("ar_content.description") }}' in template
    assert '{{ t("ar_content.create_short") }}' in template
    assert '{{ t("ar_content.delete_title") }}' in template
    assert '{{ t("ar_content.copy") }}' in template


def test_ar_content_list_template_has_no_mojibake_markers():
    template = Path("templates/ar-content/list.html").read_text(encoding="utf-8")

    assert "Р" not in template
    assert "����" not in template
