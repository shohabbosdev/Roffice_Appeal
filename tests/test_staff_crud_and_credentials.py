import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_staff_otp_generation_and_first_login_flow():
    unique_suffix = uuid.uuid4().hex[:6]
    test_username = f"test_staff_{unique_suffix}"
    renamed_username = f"official_{unique_suffix}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as Admin
        admin_login = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Admin creates a new staff member (without custom password) -> 8-character OTP generated
        create_resp = await ac.post("/api/v1/users/staff", headers=admin_headers, json={
            "username": test_username,
            "full_name": "Nodirbek Karimov",
            "role": "front_staff",
            "department_id": 1,
            "assigned_duties": "Darcha qabulida elektron navbat taloni bo'yicha xizmat ko'rsatish"
        })
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        assert created_data["must_change_password"] is True
        temp_pass = created_data["temporary_password"]
        assert len(temp_pass) == 8
        new_staff_id = created_data["user"]["id"]

        # 3. New staff logs in with temporary password
        staff_login = await ac.post("/api/v1/auth/login", json={
            "username": test_username,
            "password": temp_pass
        })
        assert staff_login.status_code == 200
        login_data = staff_login.json()
        assert login_data["must_change_password"] is True
        staff_token = login_data["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # 4. Attempt credential change with wrong current password -> 400
        bad_change = await ac.put("/api/v1/users/me/credentials", headers=staff_headers, json={
            "current_password": "WrongPassword999",
            "new_password": "SafeNewPassword2026!"
        })
        assert bad_change.status_code == 400

        # 5. Successful credential change with correct OTP
        good_change = await ac.put("/api/v1/users/me/credentials", headers=staff_headers, json={
            "current_password": temp_pass,
            "new_username": renamed_username,
            "new_password": "SafeNewPassword2026!"
        })
        assert good_change.status_code == 200
        change_data = good_change.json()
        assert change_data["must_change_password"] is False
        assert change_data["username"] == renamed_username
        assert "access_token" in change_data

        # 6. Verify old OTP no longer works
        old_login = await ac.post("/api/v1/auth/login", json={
            "username": renamed_username,
            "password": temp_pass
        })
        assert old_login.status_code == 401

        # 7. Verify new credentials work and must_change_password is now False
        new_login = await ac.post("/api/v1/auth/login", json={
            "username": renamed_username,
            "password": "SafeNewPassword2026!"
        })
        assert new_login.status_code == 200
        assert new_login.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_first_login_password_change_without_current_password():
    """Xodim birinchi marta kirganda (must_change_password=True) eski parolsiz ham faqat yangi parol bilan yangilashi mumkin."""
    unique_user = f"first_login_{uuid.uuid4().hex[:6]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        admin_login = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Yangi xodim yaratish
        resp = await ac.post("/api/v1/users/staff", headers=admin_headers, json={
            "username": unique_user,
            "full_name": "First Login Test User",
            "role": "back_staff",
            "department_id": 1
        })
        assert resp.status_code == 201
        temp_pass = resp.json()["temporary_password"]

        # 3. Yangi xodim sifatida login qilish
        staff_login = await ac.post("/api/v1/auth/login", json={
            "username": unique_user,
            "password": temp_pass
        })
        assert staff_login.status_code == 200
        assert staff_login.json()["must_change_password"] is True
        staff_token = staff_login.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # 4. Eski parolsiz (faqat new_password bilan) parolni yangilash -> 200 OK
        change_resp = await ac.put("/api/v1/users/me/credentials", headers=staff_headers, json={
            "new_password": "NewSecretPassword2026!"
        })
        assert change_resp.status_code == 200
        assert change_resp.json()["must_change_password"] is False

        # 5. Yangi parol bilan kirish muvaffaqiyatli bo'lishi kerak
        fresh_login = await ac.post("/api/v1/auth/login", json={
            "username": unique_user,
            "password": "NewSecretPassword2026!"
        })
        assert fresh_login.status_code == 200
        assert fresh_login.json()["must_change_password"] is False



@pytest.mark.asyncio
async def test_student_credential_change_blocked():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as local student
        login_resp = await ac.post("/api/v1/auth/login", json={
            "username": "student_azamat",
            "password": "StudentPass123!"
        })
        assert login_resp.status_code == 200
        student_token = login_resp.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}

        # 2. Student attempts to change credentials via backend endpoint -> 403 Forbidden (HEMIS managed)
        resp = await ac.put("/api/v1/users/me/credentials", headers=student_headers, json={
            "current_password": "StudentPass123!",
            "new_password": "HackedPassword123!"
        })
        assert resp.status_code == 403
        assert "HEMIS" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_assigned_services_and_kpi_award():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as front staff (Malika)
        malika_login = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        assert malika_login.status_code == 200
        malika_token = malika_login.json()["access_token"]
        malika_headers = {"Authorization": f"Bearer {malika_token}"}

        # 2. Malika fetches her assigned department & services
        my_srv_resp = await ac.get("/api/v1/services/my-services", headers=malika_headers)
        assert my_srv_resp.status_code == 200
        my_srv_data = my_srv_resp.json()
        assert "department" in my_srv_data
        assert "services" in my_srv_data
        assert len(my_srv_data["services"]) > 0

        # 3. Login as Office Head (Akrom)
        head_login = await ac.post("/api/v1/auth/login", json={
            "username": "akrom_head",
            "password": "HeadPass123!"
        })
        assert head_login.status_code == 200
        head_token = head_login.json()["access_token"]
        head_headers = {"Authorization": f"Bearer {head_token}"}

        # 4. Office Head awards KPI points for Nizom duty completion
        award_resp = await ac.post("/api/v1/kpi/award-points", headers=head_headers, json={
            "employee_id": 4,  # malika_front
            "duty_title": "O'qish joyidan QR-kodli elektron ma'lumotnoma rasmiylashtirish",
            "points": 10,
            "reason": "1-darchada namunali tezkor xizmat ko'rsatganligi uchun"
        })
        assert award_resp.status_code == 200
        kpi_data = award_resp.json()
        assert kpi_data["completed_points"] >= 10
        assert kpi_data["employee_id"] == 4

        # 5. Fetch Nizom duties catalog
        duties_resp = await ac.get("/api/v1/users/nizom-duties", headers=malika_headers)
        assert duties_resp.status_code == 200
        catalog = duties_resp.json()
        assert len(catalog) >= 5


@pytest.mark.asyncio
async def test_staff_update_endpoint_and_password_reset():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_login = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        # Create temporary staff to test update and password reset
        suffix = uuid.uuid4().hex[:6]
        tmp_username = f"upd_staff_{suffix}"
        c_res = await ac.post("/api/v1/users/staff", headers=admin_headers, json={
            "username": tmp_username,
            "full_name": "Test Update Staff",
            "role": "back_staff"
        })
        assert c_res.status_code == 201
        staff_id = c_res.json()["user"]["id"]

        # 1. Update staff via PUT /api/v1/users/staff/{id}
        update_resp = await ac.put(f"/api/v1/users/staff/{staff_id}", headers=admin_headers, json={
            "full_name": "Updated Staff Name",
            "reset_password": True
        })
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["user"]["full_name"] == "Updated Staff Name"
        assert update_data["new_temporary_password"] is not None
        assert len(update_data["new_temporary_password"]) == 8
        assert update_data["must_change_password"] is True

        # 2. Login with newly generated temporary password
        tmp_login = await ac.post("/api/v1/auth/login", json={
            "username": tmp_username,
            "password": update_data["new_temporary_password"]
        })
        assert tmp_login.status_code == 200
        assert tmp_login.json()["must_change_password"] is True

        # 3. Admin deletes the temporary staff member (hard delete since no appeals attached)
        del_res = await ac.delete(f"/api/v1/users/staff/{staff_id}", headers=admin_headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 4. Confirm deleted staff member is no longer in staff list
        list_res = await ac.get("/api/v1/users/staff", headers=admin_headers)
        assert list_res.status_code == 200
        staff_ids = [u["id"] for u in list_res.json()]
        assert staff_id not in staff_ids


@pytest.mark.asyncio
async def test_admin_user_and_role_protection(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Administrator hisobini va rolini tahrirlash, o'chirish yoki berish taqiqlanganligini tekshirish."""
    admin = seed_test_data["admin"]
    head = seed_test_data["head"]
    staff = seed_test_data["staff"]

    admin_token = create_token_for_user(admin.id, admin.role)
    head_token = create_token_for_user(head.id, head.role)

    # 1. Admin hisobini o'chirishga urinish -> 403 Forbidden
    del_res = await client.delete(
        f"/api/v1/users/staff/{admin.id}",
        headers={"Authorization": f"Bearer {head_token}"}
    )
    assert del_res.status_code == 403

    # 2. Admin hisobini tahrirlashga urinish (PUT /staff/{admin.id}) -> 403 Forbidden
    edit_res = await client.put(
        f"/api/v1/users/staff/{admin.id}",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"full_name": "Hacked Admin"}
    )
    assert edit_res.status_code == 403

    # 3. Admin rolini o'zgartirishga urinish (PATCH /{admin.id}/role) -> 403 Forbidden
    role_res = await client.patch(
        f"/api/v1/users/{admin.id}/role",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"role": "back_staff"}
    )
    assert role_res.status_code == 403

    # 4. Boshqa xodimga Admin rolini berishga urinish -> 403 Forbidden
    give_admin_res = await client.patch(
        f"/api/v1/users/{staff.id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "admin"}
    )
    assert give_admin_res.status_code == 403

    # 5. Yangi xodimni Admin roli bilan yaratishga urinish -> 403 Forbidden
    create_admin_res = await client.post(
        "/api/v1/users/staff",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "fake_admin_test",
            "full_name": "Fake Admin",
            "role": "admin"
        }
    )
    assert create_admin_res.status_code == 403
