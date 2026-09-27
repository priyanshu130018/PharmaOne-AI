"""Tests for Supabase Auth, RBAC, Admin access, and Multi-tenant Company Data Isolation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_missing_token_returns_401(unauthed_client: AsyncClient):
    """Protected endpoints reject requests without a Bearer token with 401."""
    resp = await unauthed_client.get("/api/v1/deviations")
    assert resp.status_code == 401
    assert "missing Bearer token" in resp.json()["detail"]

    resp_proc = await unauthed_client.post("/api/v1/deviations/process", json={"content": "test"})
    assert resp_proc.status_code == 401

    resp_sum = await unauthed_client.get("/api/v1/reports/summary")
    assert resp_sum.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(unauthed_client: AsyncClient):
    """Protected endpoints reject invalid or malformed tokens with 401."""
    resp = await unauthed_client.get(
        "/api/v1/deviations",
        headers={"Authorization": "Bearer invalid-garbage-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_returns_403(unauthed_client: AsyncClient):
    """Disabled or inactive users are rejected with 403."""
    resp = await unauthed_client.get(
        "/api/v1/deviations",
        headers={"Authorization": "Bearer test-token-inactive"},
    )
    assert resp.status_code == 403
    assert "inactive or disabled" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_returns_profile_and_membership(client: AsyncClient):
    """GET /api/v1/auth/me returns authenticated Priyanshu profile, company, and role."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "priyanshu@gmail.com"
    assert data["full_name"] == "Priyanshu"
    assert data["company_name"] == "Vasundha Pharma Chem Limited"
    assert data["role"] == "QA Manager"


@pytest.mark.asyncio
async def test_logout_records_event(client: AsyncClient):
    """POST /api/v1/auth/logout records audit event and succeeds."""
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_demo_users_endpoint_public(unauthed_client: AsyncClient):
    """GET /api/v1/auth/demo-users is public and exposes ONLY the single Priyanshu demo account."""
    resp = await unauthed_client.get("/api/v1/auth/demo-users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["email"] == "priyanshu@gmail.com"
    assert users[0]["name"] == "Priyanshu"
    assert users[0]["company"] == "Vasundha Pharma Chem Limited"
    assert users[0]["role"] == "QA Manager"
    for u in users:
        assert "password" not in u

    # Verify old demo accounts are completely purged from demo-users endpoint
    emails = [u["email"] for u in users]
    for old_email in ["rahul@gmail.com", "aman@gmail.com", "aryan@gmail.com", "rohit@gmail.com", "kartik@gmail.com"]:
        assert old_email not in emails


@pytest.mark.asyncio
async def test_company_data_isolation(
    client: AsyncClient,
    isolated_client: AsyncClient,
):
    """Rigorous tenant data isolation test.
    Priyanshu (Vasundha Pharma Chem Limited) creates a deviation.
    An isolated user (Competitor Pharma Limited) CANNOT view, list, update, or delete it.
    """
    # 1. Priyanshu creates deviation
    create_payload = {
        "title": "PharmaOne Autoclave Temperature Excursion",
        "description": "Temperature dropped to 119C during sterilization cycle in Demo Manufacturing Site.",
        "deviation_type": "equipment",
        "manufacturing_stage": "Sterilization",
        "equipment": "Autoclave AC-01",
        "source": "text",
        "impact": "patient_safety",
        "severity": "critical",
    }
    resp_create = await client.post("/api/v1/deviations", json=create_payload)
    assert resp_create.status_code == 201
    dev_data = resp_create.json()
    dev_id = dev_data["id"]

    # 2. Priyanshu can see it in his list
    resp_priyanshu_list = await client.get("/api/v1/deviations")
    assert resp_priyanshu_list.status_code == 200
    priyanshu_items = resp_priyanshu_list.json()["items"]
    assert any(d["id"] == dev_id for d in priyanshu_items)

    # 3. Priyanshu can get it by ID
    resp_priyanshu_get = await client.get(f"/api/v1/deviations/{dev_id}")
    assert resp_priyanshu_get.status_code == 200
    assert resp_priyanshu_get.json()["id"] == dev_id

    # 4. Competitor lists deviations -> CANNOT see Priyanshu's deviation
    resp_comp_list = await isolated_client.get("/api/v1/deviations")
    assert resp_comp_list.status_code == 200
    comp_items = resp_comp_list.json()["items"]
    assert not any(d["id"] == dev_id for d in comp_items)
    assert resp_comp_list.json()["total"] == 0

    # 5. Competitor tries to GET Priyanshu's deviation by ID -> 404 Not Found
    resp_comp_get = await isolated_client.get(f"/api/v1/deviations/{dev_id}")
    assert resp_comp_get.status_code == 404

    # 6. Competitor tries to UPDATE Priyanshu's deviation -> 404 Not Found
    resp_comp_put = await isolated_client.put(
        f"/api/v1/deviations/{dev_id}",
        json={"title": "Hacked Title by Competitor"},
    )
    assert resp_comp_put.status_code == 404

    # 7. Competitor tries to DELETE Priyanshu's deviation -> 404 Not Found
    resp_comp_del = await isolated_client.delete(f"/api/v1/deviations/{dev_id}")
    assert resp_comp_del.status_code == 404

    # 8. Priyanshu's deviation is still intact
    resp_priyanshu_verify = await client.get(f"/api/v1/deviations/{dev_id}")
    assert resp_priyanshu_verify.status_code == 200
    assert resp_priyanshu_verify.json()["title"] == "PharmaOne Autoclave Temperature Excursion"

    # 9. Summary reports are also isolated
    resp_priyanshu_sum = await client.get("/api/v1/reports/summary")
    assert resp_priyanshu_sum.status_code == 200
    assert resp_priyanshu_sum.json()["total"] == 1

    resp_comp_sum = await isolated_client.get("/api/v1/reports/summary")
    assert resp_comp_sum.status_code == 200
    assert resp_comp_sum.json()["total"] == 0
