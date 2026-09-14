"""ARV-031 / ARV-032 — tenant scoping of HTML admin routes.

The HTML admin panel is reachable by *every* authenticated role, not only super
admins, so each handler must scope its queries itself. These tests lock that in:
a logged-in user of one tenant must never see or mutate another tenant's
projects or notifications.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.html.routes.notifications import (
    _notification_is_visible,
    _tenant_scope_condition,
    notification_delete,
    notification_detail,
)
from app.html.routes.projects import project_detail, project_edit, projects_list
from app.html.routes.dashboard import admin_dashboard
from app.html.routes.storage import storage_page


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _user(user_id=1, company_id=10, super_admin=False):
    return SimpleNamespace(
        id=user_id,
        company_id=company_id,
        is_super_admin=super_admin,
        is_active=True,
    )


def _super_admin(user_id=99):
    return _user(user_id=user_id, company_id=None, super_admin=True)


def _notification(n_id=5, company_id=10, user_id=1):
    return SimpleNamespace(id=n_id, company_id=company_id, user_id=user_id)


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value if isinstance(self._value, list) else [self._value]


class _FakeDb:
    """Minimal async session recording every statement it is asked to run."""

    def __init__(self, get_result=None, execute_result=None):
        self.get_result = get_result
        self.execute_result = execute_result
        self.statements = []
        self.deleted = []
        self.commit_calls = 0

    async def get(self, _model, _pk):
        return self.get_result

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Result(self.execute_result)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commit_calls += 1


class _SeqDb:
    """Async session returning a different result per consecutive execute()."""

    def __init__(self, results):
        self.results = list(results)
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Result(self.results.pop(0))


def _compiled(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class _ListResult:
    """Result stub for list pages: scalar() -> 0, rows -> []."""

    def scalar(self):
        return 0

    def scalar_one_or_none(self):
        return 0

    def scalars(self):
        return self

    def all(self):
        return []


class _ListDb:
    """Async session that records statements and returns safe list results."""

    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _ListResult()


# --------------------------------------------------------------------------
# ARV-032 — notification scoping helpers
# --------------------------------------------------------------------------

def test_super_admin_sees_every_notification():
    assert _tenant_scope_condition(_super_admin()) is None
    assert _notification_is_visible(_notification(company_id=777), _super_admin()) is True


def test_tenant_user_is_scoped_to_own_company_and_self():
    condition = _tenant_scope_condition(_user(company_id=10))
    sql = str(condition)
    assert "company_id" in sql
    assert "user_id" in sql


def test_user_without_company_or_id_is_failed_closed():
    """A user we cannot attribute to a tenant must see nothing."""
    anonymous = SimpleNamespace(id=None, company_id=None, is_super_admin=False, is_active=True)
    condition = _tenant_scope_condition(anonymous)
    assert _compiled_true_is_false(condition)


def _compiled_true_is_false(condition) -> bool:
    """`false()` renders as the literal 0/false in every SQLAlchemy dialect."""
    from sqlalchemy import false
    return condition.compare(false())


def test_notification_visible_to_own_tenant():
    note = _notification(company_id=10, user_id=42)
    assert _notification_is_visible(note, _user(user_id=1, company_id=10)) is True


def test_notification_invisible_to_other_tenant():
    note = _notification(company_id=999, user_id=42)
    assert _notification_is_visible(note, _user(user_id=1, company_id=10)) is False


def test_notification_invisible_to_user_without_tenant():
    note = _notification(company_id=999, user_id=42)
    stray = SimpleNamespace(id=1, company_id=None, is_super_admin=False, is_active=True)
    assert _notification_is_visible(note, stray) is False


# --------------------------------------------------------------------------
# ARV-032 — HTML notification routes
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_delete_denies_other_tenant():
    note = _notification(company_id=999, user_id=42)
    db = _FakeDb(execute_result=note)
    request = SimpleNamespace(headers={})

    response = await notification_delete(5, request, _user(company_id=10), db)

    assert response.status_code == 403
    assert db.deleted == []
    assert db.commit_calls == 0


@pytest.mark.asyncio
async def test_notification_delete_allows_own_tenant():
    note = _notification(company_id=10, user_id=42)
    db = _FakeDb(execute_result=note)
    request = SimpleNamespace(headers={})

    response = await notification_delete(5, request, _user(company_id=10), db)

    assert response.status_code == 200
    assert db.deleted == [note]
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_notification_delete_allows_super_admin_on_foreign_tenant():
    note = _notification(company_id=999, user_id=42)
    db = _FakeDb(execute_result=note)
    request = SimpleNamespace(headers={})

    response = await notification_delete(5, request, _super_admin(), db)

    assert response.status_code == 200
    assert db.deleted == [note]


@pytest.mark.asyncio
async def test_notification_delete_reports_missing_notification():
    db = _FakeDb(execute_result=None)
    request = SimpleNamespace(headers={})

    response = await notification_delete(5, request, _user(company_id=10), db)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_notification_detail_denies_other_tenant():
    note = _notification(company_id=999, user_id=42)
    db = _FakeDb(execute_result=note)
    request = SimpleNamespace(headers={})

    response = await notification_detail(5, request, _user(company_id=10), db)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_notification_list_scopes_the_query_for_tenant_users(monkeypatch):
    """The list page must add a WHERE clause for non-super-admins."""
    from app.html.routes import notifications as mod

    seen = {}

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            seen["context"] = context
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(execute_result=[])
    request = SimpleNamespace(query_params={}, headers={})

    await mod.notifications_page(request, _user(company_id=10), db)

    # Two statements: the COUNT and the SELECT. Both must carry the scope.
    assert len(db.statements) == 2
    for stmt in db.statements:
        # Inspect the WHERE clause only: the column list always mentions
        # company_id because the model has such a column.
        where = stmt.whereclause
        assert where is not None
        assert "company_id" in str(where) or "user_id" in str(where)


@pytest.mark.asyncio
async def test_notification_list_leaves_super_admin_unscoped(monkeypatch):
    from app.html.routes import notifications as mod

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(execute_result=[])
    request = SimpleNamespace(query_params={}, headers={})

    await mod.notifications_page(request, _super_admin(), db)

    assert len(db.statements) == 2
    for stmt in db.statements:
        assert stmt.whereclause is None


# --------------------------------------------------------------------------
# ARV-031 — HTML project routes
# --------------------------------------------------------------------------

def _project(project_id=7, company_id=999):
    """Stand-in for the ORM Project (handlers call ``_pydantic_to_dict`` on it)."""
    data = {"id": project_id, "company_id": company_id, "name": "Foreign project"}
    project = SimpleNamespace(**data)
    project.model_dump = lambda exclude=None: dict(data)
    return project


@pytest.mark.asyncio
async def test_project_detail_denies_other_tenant():
    db = _FakeDb(get_result=_project(company_id=999))
    request = SimpleNamespace(headers={})

    response = await project_detail("7", request, _user(company_id=10), db)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_project_edit_denies_other_tenant():
    db = _FakeDb(get_result=_project(company_id=999))
    request = SimpleNamespace(headers={})

    response = await project_edit("7", request, _user(company_id=10), db)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_project_detail_raises_404_when_missing():
    db = _FakeDb(get_result=None)
    request = SimpleNamespace(headers={})

    with pytest.raises(HTTPException) as exc:
        await project_detail("7", request, _user(company_id=10), db)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_project_detail_allows_own_tenant(monkeypatch):
    from app.html.routes import projects as mod

    async def _fake_load_companies(db, *, current_user):
        return []

    monkeypatch.setattr(mod, "_load_project_form_companies", _fake_load_companies)

    def _build_context(request, current_user, companies, project):
        return {"request": request, "project": project}

    monkeypatch.setattr(mod, "_build_project_form_context", _build_context)

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(get_result=_project(company_id=10))
    request = SimpleNamespace(headers={})

    response = await project_detail("7", request, _user(company_id=10), db)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_project_detail_allows_super_admin_on_foreign_tenant(monkeypatch):
    from app.html.routes import projects as mod

    async def _fake_load_companies(db, *, current_user):
        return []

    monkeypatch.setattr(mod, "_load_project_form_companies", _fake_load_companies)

    def _build_context(request, current_user, companies, project):
        return {"request": request, "project": project}

    monkeypatch.setattr(mod, "_build_project_form_context", _build_context)

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(get_result=_project(company_id=999))
    request = SimpleNamespace(headers={})

    response = await project_detail("7", request, _super_admin(), db)

    assert response.status_code == 200


# --------------------------------------------------------------------------
# ARV-033 — company dropdown on the project forms
# --------------------------------------------------------------------------

def test_project_form_companies_requires_current_user():
    """The tenant filter must be impossible to forget at a call site."""
    import inspect

    from app.html.routes import projects as mod

    sig = inspect.signature(mod._load_project_form_companies)
    param = sig.parameters["current_user"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty


@pytest.mark.asyncio
async def test_project_form_companies_scoped_to_tenant():
    from app.html.routes import projects as mod

    db = _FakeDb(execute_result=[])
    await mod._load_project_form_companies(db, current_user=_user(company_id=10))

    assert len(db.statements) == 1
    where = db.statements[0].whereclause
    assert where is not None
    # Рендерится как "companies.id = :id_1" — имя таблицы, а не имя FK.
    assert "companies.id" in str(where)


@pytest.mark.asyncio
async def test_project_form_companies_unscoped_for_super_admin():
    from app.html.routes import projects as mod

    db = _FakeDb(execute_result=[])
    await mod._load_project_form_companies(db, current_user=_super_admin())

    assert len(db.statements) == 1
    assert db.statements[0].whereclause is None


@pytest.mark.asyncio
async def test_project_form_companies_fails_closed_without_company():
    """A user with no company must not see the tenant roster."""
    from app.html.routes import projects as mod

    db = _FakeDb(execute_result=[])
    stray = SimpleNamespace(id=1, company_id=None, is_super_admin=False, is_active=True)

    result = await mod._load_project_form_companies(db, current_user=stray)

    assert result == []
    assert db.statements == []


@pytest.mark.asyncio
async def test_project_form_companies_returns_serialized_rows():
    """Sanity check: the serializer is what made the leak worth fixing."""
    from app.html.routes import projects as mod

    company = SimpleNamespace(
        id=10,
        name="Acme",
        contact_email="ops@acme.test",
        status="active",
        created_at=None,
        updated_at=None,
    )
    db = _FakeDb(execute_result=[company])

    rows = await mod._load_project_form_companies(db, current_user=_user(company_id=10))

    assert rows[0]["name"] == "Acme"
    assert rows[0]["contact_email"] == "ops@acme.test"


# --------------------------------------------------------------------------
# ARV-034 — project dropdown on the AR content forms
# --------------------------------------------------------------------------

def test_projects_for_ar_form_requires_current_user():
    import inspect

    from app.html.routes import ar_content as mod

    param = inspect.signature(mod._load_projects_for_ar_form).parameters["current_user"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty


@pytest.mark.asyncio
async def test_projects_for_ar_form_scoped_to_tenant():
    from app.html.routes import ar_content as mod

    db = _FakeDb(execute_result=[])
    await mod._load_projects_for_ar_form(db, current_user=_user(company_id=10))

    assert len(db.statements) == 1
    where = db.statements[0].whereclause
    assert where is not None
    assert "company_id" in str(where)


@pytest.mark.asyncio
async def test_projects_for_ar_form_unscoped_for_super_admin():
    from app.html.routes import ar_content as mod

    db = _FakeDb(execute_result=[])
    await mod._load_projects_for_ar_form(db, current_user=_super_admin())

    assert len(db.statements) == 1
    assert db.statements[0].whereclause is None


@pytest.mark.asyncio
async def test_projects_for_ar_form_fails_closed_without_company():
    from app.html.routes import ar_content as mod

    db = _FakeDb(execute_result=[])
    stray = SimpleNamespace(id=1, company_id=None, is_super_admin=False, is_active=True)

    result = await mod._load_projects_for_ar_form(db, current_user=stray)

    assert result == []
    assert db.statements == []


# --------------------------------------------------------------------------
# ARV-035 — AR content list (customer PII)
# --------------------------------------------------------------------------

def _ar_list_request():
    return SimpleNamespace(query_params={}, headers={})


class _FakeArTemplates:
    def __init__(self):
        self.context = None

    def TemplateResponse(self, name, context, status_code=200):
        self.context = context
        from fastapi.responses import HTMLResponse

        return HTMLResponse("ok", status_code=status_code)


@pytest.mark.asyncio
async def test_ar_content_list_scopes_to_tenant(monkeypatch):
    """ARContent holds customer PII — the list must never cross tenants."""
    from app.html.routes import ar_content as mod

    fake_templates = _FakeArTemplates()
    monkeypatch.setattr(mod, "templates", fake_templates)

    # Порядок запросов: COUNT, items, company_names, statuses
    db = _SeqDb([0, [], [], []])
    await mod.ar_content_list(_ar_list_request(), _user(company_id=10), db)

    assert len(db.statements) == 4
    scoped = db.statements[:3]  # COUNT, items, company_names (statuses не sensitive)
    for stmt in scoped:
        where = stmt.whereclause
        assert where is not None
        # COUNT/items фильтруют по ar_content.company_id, фильтр имён — по companies.id
        assert "company_id" in str(where) or "companies.id" in str(where)


@pytest.mark.asyncio
async def test_ar_content_list_leaves_super_admin_unscoped(monkeypatch):
    from app.html.routes import ar_content as mod

    fake_templates = _FakeArTemplates()
    monkeypatch.setattr(mod, "templates", fake_templates)

    db = _SeqDb([0, [], [], []])
    await mod.ar_content_list(_ar_list_request(), _super_admin(), db)

    assert len(db.statements) == 4
    for stmt in db.statements[:3]:
        assert stmt.whereclause is None


@pytest.mark.asyncio
async def test_ar_content_list_fails_closed_without_company(monkeypatch):
    """A user with no company must get zero rows, not every tenant's data."""
    from app.html.routes import ar_content as mod

    fake_templates = _FakeArTemplates()
    monkeypatch.setattr(mod, "templates", fake_templates)

    db = _SeqDb([0, [], [], []])
    stray = SimpleNamespace(id=1, company_id=None, is_super_admin=False, is_active=True)

    await mod.ar_content_list(_ar_list_request(), stray, db)

    assert len(db.statements) == 4
    for stmt in db.statements[:3]:
        assert stmt.whereclause is not None


# --------------------------------------------------------------------------
# ARV-036 — project list page (cross-tenant project enumeration)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_list_scopes_to_tenant(monkeypatch):
    """The project list must scope to the caller's company, not every tenant."""
    from app.html.routes import projects as mod

    seen = {}

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            seen["context"] = context
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _ListDb()
    request = SimpleNamespace(query_params={}, headers={})

    await mod.projects_list(request, _user(company_id=10), db)

    # Count + items queries both carry the tenant WHERE; the company filter
    # dropdown is scoped to the caller's company too.
    scoped = [s for s in db.statements if s.whereclause is not None and "company_id" in str(s.whereclause)]
    assert len(scoped) == 2
    assert any("companies.id" in str(s.whereclause) for s in db.statements)


@pytest.mark.asyncio
async def test_project_list_leaves_super_admin_unscoped(monkeypatch):
    from app.html.routes import projects as mod

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _ListDb()
    request = SimpleNamespace(query_params={}, headers={})

    await mod.projects_list(request, _super_admin(), db)

    # Super admin sees every tenant — no company_id scope on the list.
    scoped = [s for s in db.statements if s.whereclause is not None and "company_id" in str(s.whereclause)]
    assert scoped == []


@pytest.mark.asyncio
async def test_project_list_fails_closed_without_company(monkeypatch):
    """A user with no company must see zero projects, not the whole platform."""
    from app.html.routes import projects as mod

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _ListDb()
    request = SimpleNamespace(query_params={}, headers={})

    stray = SimpleNamespace(id=1, company_id=None, is_super_admin=False, is_active=True)
    await mod.projects_list(request, stray, db)

    # count + items both resolve to false() (rendered as "false") — fail closed.
    project_stmts = [s for s in db.statements if "projects" in str(s).lower()]
    assert len(project_stmts) >= 2
    for s in project_stmts:
        assert str(s.whereclause) == "false"


# --------------------------------------------------------------------------
# ARV-037 — storage page (cross-tenant company roster + storage usage)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_storage_page_hides_other_tenants(monkeypatch):
    """A tenant user must only see their own company's storage row."""
    from app.html.routes import storage as mod

    async def _fake_get_storage_info(db):
        return {
            "companies": [
                {"id": 10, "name": "Acme"},
                {"id": 999, "name": "Other"},
            ]
        }

    monkeypatch.setattr(mod, "get_storage_info", _fake_get_storage_info)

    seen = {}

    class FakeTemplates:
        def TemplateResponse(self, name, context, status_code=200):
            seen["context"] = context
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok", status_code=status_code)

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    request = SimpleNamespace(headers={})
    await mod.storage_page(request, _FakeDb(), _user(company_id=10))

    companies = seen["context"]["storage_info"]["companies"]
    assert [c["id"] for c in companies] == [10]


@pytest.mark.asyncio
async def test_storage_page_shows_all_for_super_admin(monkeypatch):
    from app.html.routes import storage as mod

    async def _fake_get_storage_info(db):
        return {
            "companies": [
                {"id": 10, "name": "Acme"},
                {"id": 999, "name": "Other"},
            ]
        }

    monkeypatch.setattr(mod, "get_storage_info", _fake_get_storage_info)

    seen = {}

    class FakeTemplates:
        def TemplateResponse(self, name, context, status_code=200):
            seen["context"] = context
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok", status_code=status_code)

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    request = SimpleNamespace(headers={})
    await mod.storage_page(request, _FakeDb(), _super_admin())

    companies = seen["context"]["storage_info"]["companies"]
    assert {c["id"] for c in companies} == {10, 999}


# --------------------------------------------------------------------------
# ARV-038 — admin dashboard (platform-wide metrics disclosure)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_scopes_metrics_to_tenant(monkeypatch):
    """Tenant metrics must be scoped by company_id; super admin sees platform."""
    from app.html.routes import dashboard as mod

    seen = {}

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            seen["context"] = context
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(execute_result=[])
    request = SimpleNamespace(headers={})

    await mod.admin_dashboard(request, db, _user(company_id=10))

    # Every tenant-scoped statement carries a company_id (or companies.id) clause.
    scoped = [
        s
        for s in db.statements
        if s.whereclause is not None
        and ("company_id" in str(s.whereclause) or "companies.id" in str(s.whereclause))
    ]
    assert len(scoped) >= 4


@pytest.mark.asyncio
async def test_dashboard_leaves_super_admin_unscoped(monkeypatch):
    from app.html.routes import dashboard as mod

    class FakeTemplates:
        def TemplateResponse(self, name, context):
            from fastapi.responses import HTMLResponse

            return HTMLResponse("ok")

    monkeypatch.setattr(mod, "templates", FakeTemplates())

    db = _FakeDb(execute_result=[])
    request = SimpleNamespace(headers={})

    await mod.admin_dashboard(request, db, _super_admin())

    # Super admin has no tenant scope (only status/date filters, never company_id).
    leak = [
        s
        for s in db.statements
        if s.whereclause is not None
        and ("company_id" in str(s.whereclause) or "companies.id" in str(s.whereclause))
    ]
    assert leak == []
