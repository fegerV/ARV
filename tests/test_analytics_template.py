from pathlib import Path


def test_analytics_template_uses_partials():
    template = Path("templates/analytics.html").read_text(encoding="utf-8")
    period_filter = Path("templates/analytics/partials/period_filter.html").read_text(encoding="utf-8")
    summary_cards = Path("templates/analytics/partials/summary_cards.html").read_text(encoding="utf-8")
    views_chart = Path("templates/analytics/partials/views_chart.html").read_text(encoding="utf-8")
    engagement = Path("templates/analytics/partials/engagement_sections.html").read_text(encoding="utf-8")
    company_stats = Path("templates/analytics/partials/company_stats.html").read_text(encoding="utf-8")

    assert '{% include "analytics/partials/period_filter.html" %}' in template
    assert '{% include "analytics/partials/summary_cards.html" %}' in template
    assert '{% include "analytics/partials/views_chart.html" %}' in template
    assert '{% include "analytics/partials/engagement_sections.html" %}' in template
    assert '{% include "analytics/partials/company_stats.html" %}' in template

    assert '/analytics?period=' in period_filter
    assert 'Р’СЃРµРіРѕ РїСЂРѕСЃРјРѕС‚СЂРѕРІ' in summary_cards
    assert 'id="chart-views"' in views_chart
    assert 'id="chart-devices"' in engagement
    assert 'id="chart-browsers"' in engagement
    assert 'РЎС‚Р°С‚РёСЃС‚РёРєР° РїРѕ РєРѕРјРїР°РЅРёСЏРј' in company_stats
