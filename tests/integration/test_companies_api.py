import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_companies_crud(auth_client: AsyncClient):
    # Create
    create_res = await auth_client.post(
        "/api/companies/",
        json={
            "name": "Test Company CRUD",
            "contact_email": "crud@example.com",
        },
    )
    assert create_res.status_code == 200
    company = create_res.json()
    company_id = company["id"]
    assert company["name"] == "Test Company CRUD"

    # Read
    get_res = await auth_client.get(f"/api/companies/{company_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == company_id

    # Update
    upd_res = await auth_client.put(
        f"/api/companies/{company_id}",
        json={"name": "Test Company CRUD Updated"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == "Test Company CRUD Updated"

    # Delete (should succeed only when no projects)
    del_res = await auth_client.delete(f"/api/companies/{company_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_company_delete_blocked_when_has_projects(auth_client: AsyncClient):
    # Create company
    company_res = await auth_client.post(
        "/api/companies/",
        json={"name": "Company With Projects", "contact_email": "p@example.com"},
    )
    assert company_res.status_code == 200
    company_id = company_res.json()["id"]

    # Create project
    project_res = await auth_client.post(
        "/api/projects",
        json={"name": "Project 1", "company_id": company_id},
    )
    assert project_res.status_code == 200
    project_id = project_res.json()["id"]

    # Delete company should fail
    del_company = await auth_client.delete(f"/api/companies/{company_id}")
    assert del_company.status_code == 400

    # Clean up: delete project then company
    del_project = await auth_client.delete(f"/api/projects/{project_id}")
    assert del_project.status_code == 200
    del_company2 = await auth_client.delete(f"/api/companies/{company_id}")
    assert del_company2.status_code == 200
