from datetime import datetime
from types import SimpleNamespace


def test_require_active_user_redirects_missing_user():
    from app.html.utils import require_active_user

    response = require_active_user(None)
    assert response is not None
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_require_active_user_allows_active_user():
    from app.html.utils import require_active_user

    class User:
        is_active = True

    assert require_active_user(User()) is None


def test_serialize_fields_converts_selected_datetimes():
    from app.html.utils import serialize_fields

    payload = {
        "created_at": datetime(2026, 3, 28, 12, 0, 0),
        "updated_at": None,
        "name": "demo",
    }

    result = serialize_fields(payload, "created_at", "updated_at")
    assert result["created_at"] == "2026-03-28T12:00:00"
    assert result["updated_at"] is None
    assert result["name"] == "demo"


def test_serialize_nested_converts_nested_datetimes():
    from app.html.utils import serialize_nested

    payload = {
        "created_at": datetime(2026, 3, 28, 12, 0, 0),
        "items": [
            {"updated_at": datetime(2026, 3, 28, 13, 30, 0)},
            "plain",
        ],
    }

    result = serialize_nested(payload)
    assert result["created_at"] == "2026-03-28T12:00:00"
    assert result["items"][0]["updated_at"] == "2026-03-28T13:30:00"
    assert result["items"][1] == "plain"


def test_project_to_form_dict_serializes_project_fields():
    from app.html.routes.ar_content import _project_to_form_dict

    project = SimpleNamespace(
        id=7,
        name="Demo Project",
        status="active",
        company_id=3,
        created_at=datetime(2026, 3, 28, 10, 15, 0),
        updated_at=datetime(2026, 3, 28, 11, 45, 0),
    )

    result = _project_to_form_dict(project, ar_content_count=5)

    assert result["id"] == "7"
    assert result["name"] == "Demo Project"
    assert result["company_id"] == 3
    assert result["ar_content_count"] == 5
    assert result["created_at"] == "2026-03-28T10:15:00"
    assert result["updated_at"] == "2026-03-28T11:45:00"
    assert result["_links"]["view_content"] == "/api/projects/7/ar-content"


def test_build_ar_form_context_creates_serialized_js_payloads():
    from app.html.routes.ar_content import _build_ar_form_context

    request = object()
    current_user = object()
    companies = [
        {
            "id": 1,
            "name": "Vertex",
            "status": "active",
            "contact_email": "team@example.com",
            "created_at": datetime(2026, 3, 28, 9, 0, 0),
            "updated_at": datetime(2026, 3, 28, 9, 30, 0),
            "ignored": "value",
        }
    ]
    projects = [
        {
            "id": "11",
            "name": "Launch",
            "company_id": 1,
            "status": "active",
            "description": "Demo",
            "created_at": datetime(2026, 3, 28, 8, 0, 0),
            "updated_at": None,
            "extra": "value",
        }
    ]

    context = _build_ar_form_context(
        request,
        current_user,
        companies=companies,
        projects=projects,
        ar_content={"id": 99},
        error="boom",
    )

    assert context["request"] is request
    assert context["current_user"] is current_user
    assert context["ar_content"] == {"id": 99}
    assert context["error"] == "boom"
    assert context["companies_js"] == [
        {
            "id": 1,
            "name": "Vertex",
            "status": "active",
            "contact_email": "team@example.com",
            "created_at": "2026-03-28T09:00:00",
            "updated_at": "2026-03-28T09:30:00",
        }
    ]
    assert context["projects_js"] == [
        {
            "id": "11",
            "name": "Launch",
            "company_id": 1,
            "status": "active",
            "description": "Demo",
            "created_at": "2026-03-28T08:00:00",
            "updated_at": None,
        }
    ]


def test_serialize_company_for_project_form_serializes_dates_and_counts():
    from app.html.routes.projects import _serialize_company_for_project_form

    company = SimpleNamespace(
        id=4,
        name="Vertex",
        contact_email="team@example.com",
        status="active",
        created_at=datetime(2026, 3, 28, 14, 0, 0),
        updated_at=datetime(2026, 3, 28, 15, 30, 0),
    )

    result = _serialize_company_for_project_form(company, projects_count=8)

    assert result == {
        "id": 4,
        "name": "Vertex",
        "contact_email": "team@example.com",
        "status": "active",
        "created_at": "2026-03-28T14:00:00",
        "updated_at": "2026-03-28T15:30:00",
        "projects_count": 8,
    }


def test_build_project_form_context_includes_project_and_error():
    from app.html.routes.projects import _build_project_form_context

    request = object()
    current_user = object()
    companies = [{"id": 1, "name": "Vertex"}]
    project = {"id": "42", "name": "Launch"}

    context = _build_project_form_context(
        request,
        current_user,
        companies=companies,
        project=project,
        error="broken",
    )

    assert context == {
        "request": request,
        "companies": companies,
        "current_user": current_user,
        "project": project,
        "error": "broken",
    }


def test_build_company_form_payload_keeps_optional_fields():
    from app.html.routes.companies import _build_company_form_payload

    payload = _build_company_form_payload(
        company_id="9",
        name="Vertex",
        contact_email="team@example.com",
        status="inactive",
        storage_provider="yandex_disk",
        yandex_connected=True,
    )

    assert payload == {
        "id": "9",
        "name": "Vertex",
        "contact_email": "team@example.com",
        "status": "inactive",
        "storage_provider": "yandex_disk",
        "yandex_connected": True,
    }


def test_build_company_form_context_includes_error_when_present():
    from app.html.routes.companies import _build_company_form_context

    request = object()
    current_user = object()
    company = {"id": "1", "name": "Vertex"}

    context = _build_company_form_context(
        request,
        current_user,
        company=company,
        error="failed",
    )

    assert context == {
        "request": request,
        "company": company,
        "current_user": current_user,
        "error": "failed",
    }
