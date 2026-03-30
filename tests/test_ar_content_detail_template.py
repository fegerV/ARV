from pathlib import Path


def test_ar_content_detail_template_uses_csrf_safe_request_helper():
    template = Path("templates/ar-content/detail.html").read_text(encoding="utf-8")

    assert "request(url, options = {})" in template
    assert "X-CSRF-Token" in template
    assert "credentials: options.credentials || 'include'" in template
    assert "body instanceof FormData" in template


def test_ar_content_detail_template_has_quick_order_and_customer_actions():
    template = Path("templates/ar-content/detail.html").read_text(encoding="utf-8")

    assert "UUID:" in template
    assert "Позвонить" in template
    assert "Написать" in template
    assert "Номер заказа скопирован" in template
    assert "Открыть AR" in template
