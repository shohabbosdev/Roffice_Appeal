import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserRole
from app.services.audit_service import AuditService
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_audit_service_create_and_fetch(test_db: AsyncSession, seed_test_data: dict):
    """AuditService yordamida harakatlarni jurnallash va filtrlash testi."""
    head = seed_test_data["head"]

    # 1. Audit yozuvlarini yaratish
    await AuditService.log(
        db=test_db,
        action="update_status",
        entity_type="appeal",
        entity_id=101,
        user=head,
        changes={"old_status": "submitted", "new_status": "in_progress"},
        ip_address="192.168.1.15"
    )

    await AuditService.log(
        db=test_db,
        action="login",
        entity_type="auth",
        entity_id=head.id,
        user=head,
        changes={"method": "password"},
        ip_address="192.168.1.15"
    )

    # 2. Barcha yozuvlarni olish
    all_logs = await AuditService.get_logs(test_db, limit=50)
    assert len(all_logs) >= 2

    # 3. entity_type bo'yicha filtrlash
    appeal_logs = await AuditService.get_logs(test_db, entity_type="appeal")
    assert len(appeal_logs) == 1
    assert appeal_logs[0].entity_id == 101
    assert appeal_logs[0].action == "update_status"
    assert appeal_logs[0].user_id == head.id

    # 4. Qidiruv bo'yicha filtrlash
    search_logs = await AuditService.get_logs(test_db, search="in_progress")
    assert len(search_logs) == 1
    assert search_logs[0].entity_type == "appeal"


@pytest.mark.asyncio
async def test_audit_logs_endpoint_rbac(client: AsyncClient, seed_test_data: dict):
    """Audit loglari endpointi faqat Admin, Boshliq va Prorektor uchun ochiqligini tekshirish."""
    head = seed_test_data["head"]
    prorektor = seed_test_data["prorektor"]
    staff = seed_test_data["staff"]
    student = seed_test_data["student"]

    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    prorektor_token = create_token_for_user(prorektor.id, UserRole.VICE_RECTOR)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    student_token = create_token_for_user(student.id, UserRole.STUDENT)

    # 1. Anonim so'rov -> 401
    resp_anon = await client.get("/api/v1/audit-logs")
    assert resp_anon.status_code == 401

    # 2. Talaba so'rovi -> 403 Forbidden
    resp_student = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert resp_student.status_code == 403

    # 3. Oddiy xodim so'rovi -> 403 Forbidden
    resp_staff = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp_staff.status_code == 403

    # 4. Registrator ofisi boshlig'i -> 200 OK
    resp_head = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {head_token}"}
    )
    assert resp_head.status_code == 200
    assert isinstance(resp_head.json(), list)

    # 5. Prorektor -> 200 OK
    resp_prorektor = await client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {prorektor_token}"}
    )
    assert resp_prorektor.status_code == 200
    assert isinstance(resp_prorektor.json(), list)


@pytest.mark.asyncio
async def test_audit_logging_on_auth_login(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    """Foydalanuvchi login qilganda audit jurnaliga yozilishini tekshirish."""
    head = seed_test_data["head"]

    # 1. Login amalga oshirish
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "test_head", "password": "Pass123!"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Audit jurnali orqali tekshirish
    audit_resp = await client.get(
        "/api/v1/audit-logs?entity_type=auth&action=login",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "login"
    assert logs[0]["entity_type"] == "auth"
    assert logs[0]["user_id"] == head.id
    assert logs[0]["user_full_name"] == head.full_name
