import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_staff_services_dynamic_assignment():
    unique_suffix = uuid.uuid4().hex[:6]
    staff_username = f"spec_staff_{unique_suffix}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        admin_res = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Get available services list
        services_res = await ac.get("/api/v1/services", headers=admin_headers)
        assert services_res.status_code == 200
        all_services = services_res.json()
        assert len(all_services) >= 2
        service_id_1 = all_services[0]["id"]
        service_id_2 = all_services[1]["id"]

        # 3. Admin creates a new front_staff member with 1 service assigned initially
        create_res = await ac.post("/api/v1/users/staff", headers=admin_headers, json={
            "username": staff_username,
            "full_name": "Azizbek Rahimov",
            "role": "front_staff",
            "department_id": 1,
            "custom_password": "Password123!",
            "service_ids": [service_id_1]
        })
        assert create_res.status_code == 201
        staff_data = create_res.json()["user"]
        staff_id = staff_data["id"]
        assert len(staff_data["assigned_services"]) == 1
        assert staff_data["assigned_services"][0]["id"] == service_id_1

        # 4. Staff logs in
        staff_login = await ac.post("/api/v1/auth/login", json={
            "username": staff_username,
            "password": "Password123!"
        })
        assert staff_login.status_code == 200
        staff_token = staff_login.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # 5. Staff calls /services/my-services -> receives ONLY the 1 assigned service
        my_services_res = await ac.get("/api/v1/services/my-services", headers=staff_headers)
        assert my_services_res.status_code == 200
        my_services = my_services_res.json()["services"]
        assert len(my_services) == 1
        assert my_services[0]["id"] == service_id_1

        # 6. Admin updates assigned services via PUT /api/v1/users/{id}/services -> now 2 services
        update_assign_res = await ac.put(
            f"/api/v1/users/{staff_id}/services",
            headers=admin_headers,
            json={"service_ids": [service_id_1, service_id_2]}
        )
        assert update_assign_res.status_code == 200
        updated_services = update_assign_res.json()
        assert len(updated_services) == 2
        updated_ids = [s["id"] for s in updated_services]
        assert service_id_1 in updated_ids and service_id_2 in updated_ids

        # 7. Staff re-checks /services/my-services -> now has both services
        my_services_res2 = await ac.get("/api/v1/services/my-services", headers=staff_headers)
        assert my_services_res2.status_code == 200
        assert len(my_services_res2.json()["services"]) == 2

        # 8. Non-admin staff cannot assign services to others -> 403 Forbidden
        unauth_assign = await ac.put(
            f"/api/v1/users/{staff_id}/services",
            headers=staff_headers,
            json={"service_ids": [service_id_1]}
        )
        assert unauth_assign.status_code == 403

        # 9. Admin resets assigned services to empty -> falls back to all department services
        reset_assign_res = await ac.put(
            f"/api/v1/users/{staff_id}/services",
            headers=admin_headers,
            json={"service_ids": []}
        )
        assert reset_assign_res.status_code == 200
        assert len(reset_assign_res.json()) == 0

        # After reset, staff sees department services as fallback
        my_services_fallback = await ac.get("/api/v1/services/my-services", headers=staff_headers)
        assert my_services_fallback.status_code == 200
        assert len(my_services_fallback.json()["services"]) >= 1
