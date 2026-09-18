import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import User, UserRole


@pytest.mark.asyncio
async def test_unified_login_staff_and_student():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Staff login via unified /auth/login
        staff_resp = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        assert staff_resp.status_code == 200
        staff_data = staff_resp.json()
        assert staff_data["role"] == "front_staff"
        assert "access_token" in staff_data
        assert staff_data["expires_in_minutes"] == 720  # 12 hours

        # 2. Student login via unified /auth/login (local mock student)
        student_resp = await ac.post("/api/v1/auth/login", json={
            "username": "student_azamat",
            "password": "StudentPass123!"
        })
        assert student_resp.status_code == 200
        student_data = student_resp.json()
        assert student_data["role"] == "student"
        assert "access_token" in student_data
        assert student_data["expires_in_minutes"] == 2880  # 2 days

        # 3. Invalid credentials
        bad_resp = await ac.post("/api/v1/auth/login", json={
            "username": "nonexistent_user",
            "password": "WrongPassword123!"
        })
        assert bad_resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_staff_role_management():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login as Admin
        admin_login = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Get staff list
        staff_list_resp = await ac.get("/api/v1/users/staff", headers=admin_headers)
        assert staff_list_resp.status_code == 200
        staff_list = staff_list_resp.json()
        assert len(staff_list) > 0

        # Find Jasur (initially front_staff)
        jasur = next((u for u in staff_list if u["username"] == "jasur_front"), None)
        assert jasur is not None
        jasur_id = jasur["id"]

        # 2. Update Jasur's role to back_staff
        update_resp = await ac.patch(
            f"/api/v1/users/{jasur_id}/role",
            json={"role": "back_staff"},
            headers=admin_headers
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["role"] == "back_staff"

        # Revert Jasur's role to front_staff
        revert_resp = await ac.patch(
            f"/api/v1/users/{jasur_id}/role",
            json={"role": "front_staff"},
            headers=admin_headers
        )
        assert revert_resp.status_code == 200
        assert revert_resp.json()["role"] == "front_staff"


@pytest.mark.asyncio
async def test_non_admin_cannot_update_staff_role():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login as Front Staff (Malika)
        staff_login = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        staff_token = staff_login.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # Malika tries to view staff list
        res = await ac.get("/api/v1/users/staff", headers=staff_headers)
        assert res.status_code == 403

        # Malika tries to change a role
        res2 = await ac.patch(
            "/api/v1/users/1/role",
            json={"role": "admin"},
            headers=staff_headers
        )
        assert res2.status_code == 403
