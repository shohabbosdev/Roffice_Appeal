import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppealStatus
from app.services.appeal_service import AppealService
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_appeal_tracker_lifecycle_and_steps(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Talaba murojaatining hayotiy sikli bo'ylab vizual trek va taxminiy vaqt hisobini tekshirish."""
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, student.role)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Yangi ariza yaratiladi (SUBMITTED)
    appeal = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="Reyting daftarchasidan ko'chirma",
        message="Talabalik reyting daftarchamdan rasmiy ko'chirma berishingizni so'rayman."
    )

    # 2. Talaba trekini tekshiramiz
    resp = await client.get(f"/api/v1/appeals/{appeal.id}/track", headers=student_headers)
    assert resp.status_code == 200
    track = resp.json()
    assert track["ticket_number"] == appeal.ticket_number
    assert track["status"] == "new"
    assert track["progress_percentage"] >= 20
    assert len(track["steps"]) >= 4
    assert track["steps"][0]["step_key"] == "submitted"
    assert track["steps"][0]["status"] == "completed"
    assert track["steps"][1]["status"] == "pending"
    assert track["estimated_completion_text"] != ""

    # 3. Xodimga biriktiriladi (IN_PROGRESS)
    await AppealService.assign_appeal(
        db=test_db,
        appeal_id=appeal.id,
        staff_id=staff.id,
        assigned_by_user_id=seed_test_data["head"].id
    )

    resp_in_prog = await client.get(f"/api/v1/appeals/{appeal.id}/track", headers=student_headers)
    assert resp_in_prog.status_code == 200
    track_in_prog = resp_in_prog.json()
    assert track_in_prog["status"] in ["assigned", "in_progress"]
    assert track_in_prog["progress_percentage"] >= 50
    assert track_in_prog["assigned_staff_name"] == staff.full_name
    assert track_in_prog["steps"][1]["status"] == "current"

    # 4. Xodim hal etadi (RESOLVED)
    await AppealService.resolve_appeal(
        db=test_db,
        appeal_id=appeal.id,
        staff_id=staff.id,
        resolution_text="Ko'chirma tayyorlandi va tizimga yuklandi."
    )

    resp_resolved = await client.get(f"/api/v1/appeals/{appeal.id}/track", headers=student_headers)
    assert resp_resolved.status_code == 200
    track_resolved = resp_resolved.json()
    assert track_resolved["status"] == "resolved"
    assert track_resolved["progress_percentage"] >= 90
    assert track_resolved["resolution_text"] == "Ko'chirma tayyorlandi va tizimga yuklandi."

    # 5. Talaba tasdiqlaydi (COMPLETED)
    await AppealService.confirm_resolution(
        db=test_db,
        appeal_id=appeal.id,
        student_id=student.id,
        rating=5,
        rating_comment="Juda tezkor va a'lo darajada!"
    )

    resp_completed = await client.get(f"/api/v1/appeals/{appeal.id}/track", headers=student_headers)
    assert resp_completed.status_code == 200
    track_completed = resp_completed.json()
    assert track_completed["status"] == "completed"
    assert track_completed["progress_percentage"] == 100
    assert track_completed["rating"] == 5
    assert track_completed["steps"][-1]["status"] == "completed"


@pytest.mark.asyncio
async def test_public_appeal_tracker_and_pii_masking(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Ommaviy autentifikatsiyasiz trek va shaxsiy ma'lumotlar maskalanishini tekshirish."""
    student = seed_test_data["student"]
    service = seed_test_data["service"]

    # 1. Ariza yaratish
    appeal = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="Diplom ilovasi dublikati",
        message="Diplom ilovam yo'qolganligi sababli dublikat olishim kerak."
    )

    # 2. Ommaviy qidiruv (Hech qanday token talab etilmaydi)
    resp_pub = await client.get(f"/api/v1/appeals/track/public?ticket_number={appeal.ticket_number}")
    assert resp_pub.status_code == 200
    pub_data = resp_pub.json()
    assert pub_data["ticket_number"] == appeal.ticket_number
    assert pub_data["subject"] == appeal.subject
    assert pub_data["service_title"] == service.title
    # PII himoyasi: Talaba to'liq ismi chiqmasligi kerak!
    assert student.full_name not in pub_data["student_masked_name"]
    assert "***" in pub_data["student_masked_name"]
    assert len(pub_data["steps"]) >= 4

    # 3. '#'-siz kiritilganda ham ishlashi kerak
    raw_num = appeal.ticket_number.replace("#", "")
    resp_raw = await client.get(f"/api/v1/appeals/track/public?ticket_number={raw_num}")
    assert resp_raw.status_code == 200
    assert resp_raw.json()["ticket_number"] == appeal.ticket_number

    # 4. Mavjud bo'lmagan chipta raqamida 404
    resp_404 = await client.get("/api/v1/appeals/track/public?ticket_number=RO-9999-NOTFOUND")
    assert resp_404.status_code == 404
