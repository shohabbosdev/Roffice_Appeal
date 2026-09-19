import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import UserRole
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_service_and_department_full_crud():
    unique_suffix = uuid.uuid4().hex[:6]
    dept_code = f"DEPT_{unique_suffix}"
    service_code = f"SVC_{unique_suffix}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        admin_res = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Create department
        dept_res = await ac.post("/api/v1/services/departments", headers=headers, json={
            "name": f"Test Bolim {unique_suffix}",
            "code": dept_code,
            "dept_type": "front_office",
            "window_number": "5-darcha"
        })
        assert dept_res.status_code == 201
        dept_data = dept_res.json()
        dept_id = dept_data["id"]
        assert dept_data["code"] == dept_code

        # 3. Create service
        svc_create_res = await ac.post("/api/v1/services", headers=headers, json={
            "code": service_code,
            "title": "Diplom nusxasi berish",
            "department_id": dept_id,
            "kpi_points": 4,
            "sla_hours": 48,
            "resolution_mode": "both",
            "required_docs": "Pasport nusxasi",
            "description": "Talabaga diplom ko'chirmasini taqdim etish"
        })
        assert svc_create_res.status_code == 201
        svc_data = svc_create_res.json()
        svc_id = svc_data["id"]
        assert svc_data["code"] == service_code
        assert svc_data["kpi_points"] == 4
        assert svc_data["sla_hours"] == 48
        assert svc_data["is_active"] is True
        assert svc_data["resolution_mode"] == "both"

        # 4. Update service (edit SLA, KPI, code, resolution_mode)
        updated_code = f"UPD_{service_code}".upper()
        svc_update_res = await ac.put(f"/api/v1/services/{svc_id}", headers=headers, json={
            "code": updated_code,
            "title": "Diplom nusxasi berish (Tezlashtirilgan)",
            "sla_hours": 24,
            "kpi_points": 5,
            "resolution_mode": "online_only",
            "required_docs": "ID karta"
        })
        assert svc_update_res.status_code == 200
        updated_svc = svc_update_res.json()
        assert updated_svc["code"] == updated_code
        assert updated_svc["sla_hours"] == 24
        assert updated_svc["kpi_points"] == 5
        assert updated_svc["resolution_mode"] == "online_only"

        # 5. Toggle active status
        toggle_res = await ac.patch(f"/api/v1/services/{svc_id}/toggle-active", headers=headers)
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False

        # Verify include_inactive query param
        active_list_res = await ac.get("/api/v1/services?include_inactive=false")
        assert active_list_res.status_code == 200
        active_ids = [s["id"] for s in active_list_res.json()]
        assert svc_id not in active_ids

        all_list_res = await ac.get("/api/v1/services?include_inactive=true")
        assert all_list_res.status_code == 200
        all_ids = [s["id"] for s in all_list_res.json()]
        assert svc_id in all_ids

        # 6. Hard delete service (no appeals linked, so it gets completely deleted)
        del_res = await ac.delete(f"/api/v1/services/{svc_id}?hard_delete=true", headers=headers)
        assert del_res.status_code == 200
        assert "o'chirildi" in del_res.json()["message"]

        # Confirm deleted
        get_deleted_res = await ac.get(f"/api/v1/services/{svc_id}")
        assert get_deleted_res.status_code == 404

        # 7. Update department
        dept_upd_res = await ac.put(f"/api/v1/services/departments/{dept_id}", headers=headers, json={
            "name": f"Yangilangan Bolim {unique_suffix}",
            "code": f"NEW_{dept_code}",
            "dept_type": "back_office",
            "window_number": "6-darcha"
        })
        assert dept_upd_res.status_code == 200
        assert dept_upd_res.json()["name"] == f"Yangilangan Bolim {unique_suffix}"
        assert dept_upd_res.json()["window_number"] == "6-darcha"

        # 8. Delete department
        dept_del_res = await ac.delete(f"/api/v1/services/departments/{dept_id}?hard_delete=true", headers=headers)
        assert dept_del_res.status_code == 200
        assert "o'chirildi" in dept_del_res.json()["message"]


@pytest.mark.asyncio
async def test_office_head_can_manage_departments(client: AsyncClient, seed_test_data):
    head = seed_test_data["head"]
    token = create_access_token(
        data={"sub": str(head.id), "role": UserRole.OFFICE_HEAD.value, "username": head.username}
    )
    headers = {"Authorization": f"Bearer {token}"}

    suffix = uuid.uuid4().hex[:6]
    # Office head creates department
    create_res = await client.post("/api/v1/services/departments", headers=headers, json={
        "name": f"Office Head Dept {suffix}",
        "code": f"OH_{suffix}",
        "dept_type": "front_office",
        "window_number": "10-darcha"
    })
    assert create_res.status_code == 201
    dept_id = create_res.json()["id"]

    # Office head updates department
    upd_res = await client.put(f"/api/v1/services/departments/{dept_id}", headers=headers, json={
        "name": f"Office Head Dept Updated {suffix}",
        "window_number": "11-darcha"
    })
    assert upd_res.status_code == 200

    # Office head deletes department
    del_res = await client.delete(f"/api/v1/services/departments/{dept_id}?hard_delete=true", headers=headers)
    assert del_res.status_code == 200
