from __future__ import annotations


def test_list_employees_requires_auth(client):
    resp = client.get("/api/employees/")
    assert resp.status_code == 401


def test_list_employees(client, auth_headers, registered_user):
    resp = client.get("/api/employees/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


def test_search_employees_by_name(client, auth_headers, registered_user):
    name_fragment = registered_user["full_name"][:4]
    resp = client.get(f"/api/employees/?search={name_fragment}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(
        registered_user["full_name"] in emp["full_name"] for emp in data["items"]
    )


def test_get_employee_by_id(client, auth_headers):
    # Get employee list first to find a valid ID
    list_resp = client.get("/api/employees/", headers=auth_headers)
    items = list_resp.get_json()["items"]
    assert items, "Expected at least one employee"

    emp_id = items[0]["id"]
    resp = client.get(f"/api/employees/{emp_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["id"] == emp_id


def test_get_nonexistent_employee(client, auth_headers):
    resp = client.get("/api/employees/999999", headers=auth_headers)
    assert resp.status_code == 404
