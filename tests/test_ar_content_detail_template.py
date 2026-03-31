from pathlib import Path


def test_ar_content_detail_template_uses_csrf_safe_request_helper():
    template = Path("templates/ar-content/detail.html").read_text(encoding="utf-8")

    assert "request(url, options = {})" in template
    assert "X-CSRF-Token" in template
    assert "credentials: options.credentials || 'include'" in template
    assert "body instanceof FormData" in template


def test_ar_content_detail_template_has_quick_order_and_customer_actions():
    template = Path("templates/ar-content/detail.html").read_text(encoding="utf-8")
    header = Path("templates/ar-content/partials/detail_header.html").read_text(encoding="utf-8")
    overview = Path("templates/ar-content/partials/detail_overview.html").read_text(encoding="utf-8")
    links_and_marker = Path("templates/ar-content/partials/detail_links_and_marker.html").read_text(encoding="utf-8")
    marker_quality = Path("templates/ar-content/partials/detail_marker_quality.html").read_text(encoding="utf-8")
    video_panel = Path("templates/ar-content/partials/detail_video_panel_intro.html").read_text(encoding="utf-8")
    video_list = Path("templates/ar-content/partials/detail_video_list.html").read_text(encoding="utf-8")
    rotation_overview = Path("templates/ar-content/partials/detail_rotation_overview.html").read_text(encoding="utf-8")
    rotation_dialog = Path("templates/ar-content/partials/detail_rotation_dialog.html").read_text(encoding="utf-8")
    media_modals = Path("templates/ar-content/partials/detail_media_modals.html").read_text(encoding="utf-8")
    joined = "\n".join([template, header, overview, links_and_marker, marker_quality, video_panel, video_list, rotation_overview, rotation_dialog, media_modals])

    assert '{% include "ar-content/partials/detail_header.html" %}' in template
    assert '{% include "ar-content/partials/detail_overview.html" %}' in template
    assert '{% include "ar-content/partials/detail_links_and_marker.html" %}' in template
    assert '{% include "ar-content/partials/detail_marker_quality.html" %}' in template
    assert '{% include "ar-content/partials/detail_video_panel_intro.html" %}' in template
    assert '{% include "ar-content/partials/detail_video_list.html" %}' in template
    assert '{% include "ar-content/partials/detail_rotation_overview.html" %}' in template
    assert '{% include "ar-content/partials/detail_rotation_dialog.html" %}' in template
    assert '{% include "ar-content/partials/detail_media_modals.html" %}' in template
    assert "UUID:" in joined
    assert "Позвонить" in joined
    assert "Написать" in joined
    assert "Номер заказа скопирован" in joined
    assert "Открыть AR" in joined
    assert "Управление видео" in joined
    assert "Расписание ротации видео" in joined
    assert "Все видео" in joined
    assert "Настройка расписания ротации" in joined
    assert "Маркер и качество" in joined
    assert "Загрузить видео" in joined
    assert "Удалить AR контент" in joined


def test_ar_content_detail_template_reuses_embedded_videos_before_refetch():
    template = Path("templates/ar-content/detail.html").read_text(encoding="utf-8")

    assert "if (Array.isArray(this.videos) && this.videos.length > 0)" in template
    assert "this.playbackMode = this.inferPlaybackMode();" in template
    assert "this.loadVideos();" in template
