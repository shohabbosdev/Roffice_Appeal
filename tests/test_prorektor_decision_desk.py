import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Appeal, AppealStatus, UserRole
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_prorektor_decision_on_escalated_appeal(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]
    prorektor = seed_test_data["prorektor"]

    # 1. Boshliq tomonidan prorektorga eskalatsiya qilingan ariza
    appeal = Appeal(
        ticket_number="APP-PROREKTOR-01",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.ESCALATED_PROREKTOR,
        subject="Qayta tiklash to'g'risida ariza",
        message="Talabalar safidan chetlashtirilgan edim, qayta tiklashni so'rayman",
        clarification_message="Boshliq izohi: Talabaning akademik qarzlari bo'yicha maxsus komissiya xulosasi zarur.",
        earned_kpi_points=4
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)

    prorektor_token = create_access_token({"sub": str(prorektor.id), "role": UserRole.VICE_RECTOR.value})
    headers = {"Authorization": f"Bearer {prorektor_token}"}

    # 2. Prorektor yakuniy qaror chiqaradi
    decision_text = "Murojaat komissiya tomonidan ko'rib chiqildi va ijobiy hal etildi. 3-semestrdan o'qishga qayta tiklansin."
    resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/prorektor-decision",
        headers=headers,
        json={"final_decision": decision_text}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert decision_text in data["resolution_text"]
    assert data["closed_at"] is not None


@pytest.mark.asyncio
async def test_prorektor_decision_on_disputed_appeal(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]
    prorektor = seed_test_data["prorektor"]

    # 1. Talaba tomonidan e'tiroz bildirilgan (nizoli) ariza
    appeal = Appeal(
        ticket_number="APP-DISPUTE-02",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.DISPUTED,
        subject="Reyting daftarchasi masalasi",
        message="Baholarim ko'rinmayapti",
        resolution_text="Tizimda baholar mavjud emas deb javob berilgan",
        dispute_reason="Fanning yakuniy nazorati qaydnomasini taqdim etganman, asossiz rad etildi.",
        earned_kpi_points=4
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)

    prorektor_token = create_access_token({"sub": str(prorektor.id), "role": UserRole.VICE_RECTOR.value})
    headers = {"Authorization": f"Bearer {prorektor_token}"}

    # 2. Prorektor to'g'ridan-to'g'ri nizo bo'yicha yakuniy qaror chiqaradi
    decision_text = "Qaydnomalar tekshirildi va HEMIS tizimiga kiritildi. Xodimga ogohlantirish berildi."
    resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/prorektor-decision",
        headers=headers,
        json={"final_decision": decision_text}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert decision_text in data["resolution_text"]


@pytest.mark.asyncio
async def test_non_prorektor_forbidden_from_decision(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    appeal = Appeal(
        ticket_number="APP-PROREKTOR-03",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.ESCALATED_PROREKTOR,
        subject="Muhim masala",
        message="Ariza matni",
        earned_kpi_points=4
    )
    test_db.add(appeal)
    await test_db.commit()
    await test_db.refresh(appeal)

    # Oddiy front xodim tokeni
    staff_token = create_access_token({"sub": str(staff.id), "role": UserRole.FRONT_STAFF.value})
    headers = {"Authorization": f"Bearer {staff_token}"}

    resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/prorektor-decision",
        headers=headers,
        json={"final_decision": "Noqonuniy qaror"}
    )
    assert resp.status_code == 403
