from pathlib import Path


def test_analytics_template_uses_i18n_labels():
    template = Path("templates/analytics.html").read_text(encoding="utf-8")
    period = Path("templates/analytics/partials/period_filter.html").read_text(encoding="utf-8")
    summary = Path("templates/analytics/partials/summary_cards.html").read_text(encoding="utf-8")
    engagement = Path("templates/analytics/partials/engagement_sections.html").read_text(encoding="utf-8")
    company_stats = Path("templates/analytics/partials/company_stats.html").read_text(encoding="utf-8")

    assert '{{ t("analytics.title") }}' in template
    assert '{{ t("analytics.period") }}' in period
    assert '{{ t("analytics.total_views") }}' in summary
    assert '{{ t("analytics.top_content") }}' in engagement
    assert '{{ t("analytics.company_stats") }}' in company_stats
