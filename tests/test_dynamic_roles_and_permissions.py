import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.permissions import PERMISSIONS_CATALOG


@pytest.mark.asyncio
async def test_dynamic_roles_and_permissions_full_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        admin_login = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        assert admin_login.json()["permissions"] == ["*"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Permissions catalog test
        cat_res = await ac.get("/api/v1/roles/catalog", headers=admin_headers)
        assert cat_res.status_code == 200
        catalog = cat_res.json()["catalog"]
        assert len(catalog) >= 20
        cat_codes = [p["code"] for p in catalog]
        assert "appeals:view_all" in cat_codes
        assert "roles:manage" in cat_codes
        assert "system:integrations" in cat_codes

        # 3. List roles
        roles_res = await ac.get("/api/v1/roles", headers=admin_headers)
        assert roles_res.status_code == 200
        roles = roles_res.json()
        assert len(roles) >= 6
        role_map = {r["code"]: r for r in roles}
        assert "admin" in role_map
        assert "office_head" in role_map
        assert "front_staff" in role_map
        assert "student" in role_map

        admin_role = role_map["admin"]
        assert admin_role["is_immutable"] is True
        assert admin_role["is_system"] is True
        assert admin_role["permissions"] == ["*"]

        # 4. Admin role and system roles protection
        admin_update = await ac.put(f"/api/v1/roles/{admin_role['id']}", headers=admin_headers, json={
            "name": "Buzilgan Admin",
            "permissions": []
        })
        assert admin_update.status_code == 400
        assert "Bosh administrator" in admin_update.json()["detail"]

        admin_delete = await ac.delete(f"/api/v1/roles/{admin_role['id']}", headers=admin_headers)
        assert admin_delete.status_code == 400

        office_head_role = role_map["office_head"]
        head_delete = await ac.delete(f"/api/v1/roles/{office_head_role['id']}", headers=admin_headers)
        assert head_delete.status_code == 400
        assert "standart shablon" in head_delete.json()["detail"]

        # 5. Create custom role
        suffix = uuid.uuid4().hex[:6]
        custom_code = f"yurist_{suffix}"
        create_res = await ac.post("/api/v1/roles", headers=admin_headers, json={
            "code": custom_code,
            "name": "Bosh Huquqshunos",
            "description": "Yuridik maslahat va murojaatlarni huquqiy ko'rish",
            "permissions": ["appeals:view_all", "appeals:resolve"]
        })
        assert create_res.status_code == 201
        created_role = create_res.json()
        assert created_role["code"] == custom_code
        assert set(created_role["permissions"]) == {"appeals:view_all", "appeals:resolve"}
        assert created_role["is_system"] is False

        # 6. Update custom role
        update_res = await ac.put(f"/api/v1/roles/{created_role['id']}", headers=admin_headers, json={
            "name": "Yetakchi Huquqshunos",
            "description": "Kengaytirilgan yuridik vakolatlar",
            "permissions": ["appeals:view_all", "appeals:resolve", "appeals:reject"]
        })
        assert update_res.status_code == 200
        updated_role = update_res.json()
        assert updated_role["name"] == "Yetakchi Huquqshunos"
        assert set(updated_role["permissions"]) == {"appeals:view_all", "appeals:resolve", "appeals:reject"}

        # 6.1 List roles after custom role creation (must not 500 on non-enum role codes)
        list_after_custom = await ac.get("/api/v1/roles", headers=admin_headers)
        assert list_after_custom.status_code == 200
        assert any(r["code"] == custom_code for r in list_after_custom.json())

        # 7. Staff individual override permissions
        # Find a staff user (e.g. malika_front or another staff)
        staff_login = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        assert staff_login.status_code == 200
        staff_data = staff_login.json()
        staff_id = staff_data["user_id"]
        staff_headers = {"Authorization": f"Bearer {staff_data['access_token']}"}

        # Check staff initial permissions via /me
        me_res = await ac.get("/api/v1/auth/me", headers=staff_headers)
        assert me_res.status_code == 200
        assert "effective_permissions" in me_res.json()

        # Non-admin cannot manage roles or view all roles
        forbidden_create = await ac.post("/api/v1/roles", headers=staff_headers, json={
            "code": "hacker_role",
            "name": "Hacker",
            "permissions": ["*"]
        })
        assert forbidden_create.status_code == 403

        # Admin assigns individual override permission to staff: "audit:view"
        staff_perm_res = await ac.get(f"/api/v1/roles/staff/{staff_id}/permissions", headers=admin_headers)
        assert staff_perm_res.status_code == 200
        staff_perm_data = staff_perm_res.json()
        assert staff_perm_data["user_id"] == staff_id

        # Update override permissions
        set_override = await ac.put(
            f"/api/v1/roles/staff/{staff_id}/permissions",
            headers=admin_headers,
            json={"custom_permissions": ["audit:view", "analytics:view"]}
        )
        assert set_override.status_code == 200
        override_data = set_override.json()
        assert "audit:view" in override_data["effective_permissions"]
        assert "analytics:view" in override_data["effective_permissions"]

        # 8. Delete custom role
        del_res = await ac.delete(f"/api/v1/roles/{created_role['id']}", headers=admin_headers)
        assert del_res.status_code == 200
        assert "muvaffaqiyatli" in del_res.json()["message"]
