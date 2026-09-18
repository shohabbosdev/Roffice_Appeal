import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, AppealStatus
from app.services.kpi_service import KPIService


async def test_full_appeal_lifecycle(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    head = seed_test_data["head"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)

    # 1. Student submits an appeal
    create_resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "subject": "Talabalik to'g'risida ma'lumotnoma so'rovi",
            "message": "Ish joyiga taqdim etish uchun ma'lumotnoma kerak."
        }
    )
    assert create_resp.status_code == 201
    appeal_data = create_resp.json()
    appeal_id = appeal_data["id"]
    assert appeal_data["status"] == AppealStatus.NEW.value
    assert appeal_data["ticket_number"].startswith("APP-")
    assert appeal_data["sla_deadline_at"] is not None

    # 2. Anti-spam verification: Duplicate open appeal for same service must fail
    spam_resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "subject": "Takroriy so'rov",
            "message": "Nega javob berilmadi?"
        }
    )
    assert spam_resp.status_code == 400
    assert "faol murojaat mavjud" in spam_resp.json()["detail"]

    # 3. Office Head assigns appeal to Front Staff
    assign_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"staff_id": staff.id}
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == AppealStatus.ASSIGNED.value
    assert assign_resp.json()["assigned_staff_id"] == staff.id

    # 4. Staff requests clarification from student
    clarify_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/request-clarification",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"clarification_message": "Ma'lumotnoma qaysi tashkilot nomiga berilishi kerak?"}
    )
    assert clarify_resp.status_code == 200
    assert clarify_resp.json()["status"] == AppealStatus.CLARIFICATION_NEEDED.value

    # 5. Student provides clarification
    provide_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/provide-clarification",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"additional_info": "'O'zbektelekom' AK Jizzax filiali nomiga"}
    )
    assert provide_resp.status_code == 200
    assert provide_resp.json()["status"] == AppealStatus.IN_PROGRESS.value

    # 6. Staff resolves appeal
    resolve_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "resolution_text": "Ma'lumotnoma rasmiylashtirildi va ilova qilindi.",
            "result_file_url": "https://storage.jbnuu.uz/certificates/app-101.pdf"
        }
    )
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["status"] == AppealStatus.RESOLVED.value
    assert res_data["qr_hash"] is not None
    assert res_data["confirmation_deadline_at"] is not None

    # 7. Student confirms resolution and rates 5 stars
    confirm_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/confirm",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "rating": 5,
            "rating_comment": "Tez va sifatli xizmat ko'rsatildi, rahmat!"
        }
    )
    assert confirm_resp.status_code == 200
    conf_data = confirm_resp.json()
    assert conf_data["status"] == AppealStatus.COMPLETED.value
    assert conf_data["rating"] == 5

    # 8. Verify staff received KPI points
    # NOTE: KPI ball resolve paytida avtomatik beriladi (service.kpi_points),
    # va confirm paytida yana 0 ball (faqat rating yangilanadi).
    # Shu sababli completed_points >= service.kpi_points bo'lishi kerak.
    kpi = await KPIService.get_or_create_monthly_target(test_db, staff.id, "2026-09")
    assert kpi.completed_points >= service.kpi_points, (
        f"KPI ball yetarli emas: {kpi.completed_points} < {service.kpi_points}"
    )
    assert kpi.total_appeals_completed >= 1


async def test_appeal_authorization_checks(client: AsyncClient, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # 1. Staff cannot create appeals
    staff_create_resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"service_id": service.id, "subject": "Test", "message": "Test"}
    )
    assert staff_create_resp.status_code == 403

    # 2. Student cannot assign appeals
    student_assign_resp = await client.post(
        "/api/v1/appeals/1/assign",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"staff_id": staff.id}
    )
    assert student_assign_resp.status_code == 403


async def test_kunduzgi_student_forbidden_from_online_appeal(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Kunduzgi ta'lim shakli talabasi onlayn murojaat yo'llay olmasligi, faqat sirtqi/masofaviy yo'llay olishi testi."""
    from app.models import User
    from app.core.security import hash_password

    # Kunduzgi talaba yaratish
    kunduzgi_student = User(
        username="kunduzgi_user",
        hashed_password=hash_password("Pass123!"),
        full_name="Kunduzgi Talaba",
        role=UserRole.STUDENT,
        hemis_student_id="HEMIS-KUNDUZGI-01",
        education_form="Kunduzgi"
    )
    test_db.add(kunduzgi_student)
    await test_db.commit()

    service = seed_test_data["service"]
    kunduzgi_token = create_token_for_user(kunduzgi_student.id, UserRole.STUDENT)

    # 1. Kunduzgi talaba onlayn murojaat yo'llashga urinadi -> 403 Forbidden
    resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {kunduzgi_token}"},
        json={
            "service_id": service.id,
            "subject": "Kunduzgi murojaat",
            "message": "Ma'lumotnoma kerak"
        }
    )
    assert resp.status_code == 403
    assert "faqat sirtqi va masofaviy" in resp.json()["detail"]

