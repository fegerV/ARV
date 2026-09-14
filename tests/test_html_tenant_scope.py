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
from app.html.routes.projects import project_detail, project_edit


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


def _compiled(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


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

    async def _fake_load_companies(db):
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

    async def _fake_load_companies(db):
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
