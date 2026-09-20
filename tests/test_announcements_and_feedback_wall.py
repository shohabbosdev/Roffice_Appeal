import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, UserRole, Appeal, AppealStatus, Service, Announcement, AnnouncementPriority
from app.services.appeal_service import AppealService
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_pending_feedback_endpoint_and_blocking_actions(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Hal etilgan arizasi bor talaba yangi xizmat ololmasligi va baholagach ruxsat berilishini tekshirish."""
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, student.role)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Boshida pending feedback yo'q
    resp = await client.get("/api/v1/appeals/pending-feedback", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json() is None

    # 2. Yangi ariza yaratib, xodim uni RESOLVED qiladi
    appeal = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="Ma'lumotnoma olish",
        message="Talabalik ma'lumotnomasi kerak."
    )
    resolved_appeal = await AppealService.resolve_appeal(
        db=test_db,
        appeal_id=appeal.id,
        staff_id=staff.id,
        resolution_text="Ma'lumotnoma tayyorlab berildi."
    )
    assert resolved_appeal.status == AppealStatus.RESOLVED

    # 3. Endi pending-feedback tekshirilganda arizani qaytaradi
    resp_pending = await client.get("/api/v1/appeals/pending-feedback", headers=student_headers)
    assert resp_pending.status_code == 200
    pending_data = resp_pending.json()
    assert pending_data is not None
    assert pending_data["id"] == appeal.id
    assert pending_data["ticket_number"] == appeal.ticket_number

    # 4. Talaba yana boshqa ariza bermoqchi bo'lsa -> 400 BAD REQUEST bilan to'xtatiladi
    resp_new_app = await client.post(
        "/api/v1/appeals",
        headers=student_headers,
        json={
            "service_id": service.id,
            "subject": "Ikkinchi ariza",
            "message": "Menga yana boshqa xizmat kerak."
        }
    )
    assert resp_new_app.status_code == 400
    assert "oldingi arizangiz natijasini tasdiqlang" in resp_new_app.json()["detail"]

    # 5. Talaba navbat olmoqchi bo'lsa -> 400 BAD REQUEST bilan to'xtatiladi
    resp_book = await client.post(
        "/api/v1/appointments/book",
        headers=student_headers,
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "10:00 - 10:15"
        }
    )
    assert resp_book.status_code == 400
    assert "hali tasdiqlanmagan arizangiz mavjud" in resp_book.json()["detail"]

    # 6. Talaba arizani tasdiqlaydi va baholaydi (Rating = 5)
    resp_confirm = await client.post(
        f"/api/v1/appeals/{appeal.id}/confirm",
        headers=student_headers,
        json={
            "rating": 5,
            "rating_comment": "Juda tez va sifatli xizmat!"
        }
    )
    assert resp_confirm.status_code == 200
    assert resp_confirm.json()["status"] == "completed"

    # 7. Tasdiqlangach, pending feedback yana bo'sh bo'ladi
    resp_pending_after = await client.get("/api/v1/appeals/pending-feedback", headers=student_headers)
    assert resp_pending_after.status_code == 200
    assert resp_pending_after.json() is None


@pytest.mark.asyncio
async def test_targeted_announcements_flow(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Segmentatsiyalangan e'lonlar, o'qilganlik fiksatsiyasi, analitika va CSV eksport oqimini tekshirish."""
    student = seed_test_data["student"] # Sirtqi talaba
    head = seed_test_data["head"]

    head_token = create_token_for_user(head.id, head.role)
    head_headers = {"Authorization": f"Bearer {head_token}"}

    student_token = create_token_for_user(student.id, student.role)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Xodim/Boshliq tomonidan faqat 'Sirtqi' talabalar uchun e'lon chiqariladi
    resp_create = await client.post(
        "/api/v1/announcements",
        headers=head_headers,
        json={
            "title": "Sirtqi ta'lim sessiya jadvallari",
            "content": "Hurmatli talabalar, kuzgi sessiya 1-oktyabrdan boshlanadi.",
            "priority": "important",
            "target_education_form": "Sirtqi",
            "requires_ack": True,
            "send_telegram": False
        }
    )
    assert resp_create.status_code == 201
    ann_data = resp_create.json()
    ann_id = ann_data["id"]
    assert ann_data["title"] == "Sirtqi ta'lim sessiya jadvallari"

    # 2. Sirtqi talaba o'ziga mos e'lonni ko'radi
    resp_student_anns = await client.get("/api/v1/announcements/my", headers=student_headers)
    assert resp_student_anns.status_code == 200
    student_anns = resp_student_anns.json()
    assert len(student_anns) >= 1
    target_ann = next(a for a in student_anns if a["id"] == ann_id)
    assert target_ann["is_read"] is False
    assert target_ann["is_acknowledged"] is False

    # 3. Talaba e'lonni o'qiydi va "Tanishdim" deb tasdiqlaydi
    resp_read = await client.post(
        f"/api/v1/announcements/{ann_id}/read?is_ack=true",
        headers=student_headers
    )
    assert resp_read.status_code == 200
    assert resp_read.json()["is_acknowledged"] is True

    # 4. Talabaning e'lonlarida o'qilganlik aks etadi
    resp_student_anns_after = await client.get("/api/v1/announcements/my", headers=student_headers)
    target_ann_after = next(a for a in resp_student_anns_after.json() if a["id"] == ann_id)
    assert target_ann_after["is_read"] is True
    assert target_ann_after["is_acknowledged"] is True

    # 5. Xodim ushbu e'lon bo'yicha jonli analitikani oladi
    resp_ana = await client.get(f"/api/v1/announcements/{ann_id}/analytics", headers=head_headers)
    assert resp_ana.status_code == 200
    ana_data = resp_ana.json()
    assert ana_data["total_target_students"] >= 1
    assert ana_data["read_count"] >= 1
    assert ana_data["acknowledged_count"] >= 1
    assert ana_data["read_percentage"] > 0

    # 6. O'qimagan talabalar ro'yxatini Excel (.xls) va CSV formatlarida yuklab olish
    resp_export = await client.get(f"/api/v1/announcements/{ann_id}/unread-export?format=xls", headers=head_headers)
    assert resp_export.status_code == 200
    assert "excel" in resp_export.headers.get("content-type", "")

    resp_export_csv = await client.get(f"/api/v1/announcements/{ann_id}/unread-export?format=csv", headers=head_headers)
    assert resp_export_csv.status_code == 200
    assert "text/csv" in resp_export_csv.headers.get("content-type", "")

    # 7. E'lonni bekor qilish / o'chirish
    resp_del = await client.delete(f"/api/v1/announcements/{ann_id}", headers=head_headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "success"
