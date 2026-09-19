import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Appeal, AppealStatus, UserRole
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_student_portal_confirm_with_rating(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    # 1. Talaba nomidan murojaat yaratamiz
    appeal = Appeal(
        ticket_number="APP-PORTAL-01",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.RESOLVED,
        subject="Akademik ma'lumotnoma so'rovi",
        message="Menga 3-kursni tugatganlik haqida ma'lumotnoma kerak",
        resolution_text="Ma'lumotnoma rasmiylashtirildi va tizimga biriktirildi.",
        result_file_url="/static/uploads/results/sample_doc.pdf",
        earned_kpi_points=4
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)

    student_token = create_access_token({"sub": str(student.id), "role": UserRole.STUDENT.value})
    headers = {"Authorization": f"Bearer {student_token}"}

    # 2. Talaba o'z murojaatlarini ko'radi va ijrochi javobi hamda fayli borligini tekshiradi
    resp = await client.get("/api/v1/appeals", headers=headers)
    assert resp.status_code == 200
    appeals = resp.json()
    assert len(appeals) >= 1
    target = next((a for a in appeals if a["id"] == appeal.id), None)
    assert target is not None
    assert target["resolution_text"] == "Ma'lumotnoma rasmiylashtirildi va tizimga biriktirildi."
    assert target["result_file_url"] == "/static/uploads/results/sample_doc.pdf"
    assert target["status"] == "resolved"

    # 3. Talaba portal interaktiv modali orqali 5 yulduzli baho va izoh bilan tasdiqlaydi
    confirm_resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/confirm",
        headers=headers,
        json={
            "rating": 5,
            "rating_comment": "Xizmat ko'rsatish juda tez va a'lo darajada bajarildi!"
        }
    )
    assert confirm_resp.status_code == 200
    confirmed_data = confirm_resp.json()
    assert confirmed_data["status"] == "completed"
    assert confirmed_data["rating"] == 5
    assert confirmed_data["rating_comment"] == "Xizmat ko'rsatish juda tez va a'lo darajada bajarildi!"


@pytest.mark.asyncio
async def test_student_portal_dispute(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    # 1. Hal etilgan holatdagi ariza
    appeal = Appeal(
        ticket_number="APP-PORTAL-02",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.RESOLVED,
        subject="Reyting daftarchasidan ko'chirma",
        message="Ko'chirma kerak",
        resolution_text="Ko'chirma taqdim etildi.",
        earned_kpi_points=4
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)

    student_token = create_access_token({"sub": str(student.id), "role": UserRole.STUDENT.value})
    headers = {"Authorization": f"Bearer {student_token}"}

    # 2. Talaba asosli e'tiroz bildiradi (dispute modal orqali)
    dispute_resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/dispute",
        headers=headers,
        json={
            "dispute_reason": "Taqdim etilgan ko'chirmada 2 ta fan bo'yicha baho xato ko'rsatilgan."
        }
    )
    assert dispute_resp.status_code == 200
    disputed_data = dispute_resp.json()
    assert disputed_data["status"] == "disputed"
    assert "xato ko'rsatilgan" in disputed_data["dispute_reason"]


@pytest.mark.asyncio
async def test_student_portal_appointments_list(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    service = seed_test_data["service"]

    student_token = create_access_token({"sub": str(student.id), "role": UserRole.STUDENT.value})
    headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Talaba navbat oladi
    book_resp = await client.post(
        "/api/v1/appointments/book",
        headers=headers,
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-25",
            "time_slot": "10:00 - 10:15"
        }
    )
    assert book_resp.status_code == 201
    ticket = book_resp.json()
    assert "ticket_code" in ticket
    assert ticket["window_number"] is not None

    # 2. Talaba portaldagi 'Mening navbat talonlarim' ro'yxatini yuklaydi
    list_resp = await client.get("/api/v1/appointments", headers=headers)
    assert list_resp.status_code == 200
    appointments = list_resp.json()
    assert len(appointments) >= 1
    my_ticket = next((a for a in appointments if a["id"] == ticket["id"]), None)
    assert my_ticket is not None
    assert my_ticket["ticket_code"] == ticket["ticket_code"]
    assert my_ticket["appointment_date"] == "2026-09-25"
    assert my_ticket["time_slot"] == "10:00 - 10:15"
