import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, Appeal, AppealStatus, Appointment, AppointmentStatus
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_live_badges_flow(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    head = seed_test_data["head"]
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # 1. Unauthenticated request gets 401
    unauth_res = await client.get("/api/v1/appeals/live-badges")
    assert unauth_res.status_code == 401

    # 2. Student user gets 403 Forbidden
    student_res = await client.get("/api/v1/appeals/live-badges", headers={"Authorization": f"Bearer {student_token}"})
    assert student_res.status_code == 403

    # 3. Staff user gets 200 OK
    staff_res = await client.get("/api/v1/appeals/live-badges", headers={"Authorization": f"Bearer {staff_token}"})
    assert staff_res.status_code == 200
    data = staff_res.json()
    assert "new_appeals" in data
    assert "my_assigned" in data
    assert "disputed_appeals" in data
    assert "urgent_sla_appeals" in data
    assert "today_waiting_appointments" in data
    assert "last_appeal_id" in data
    assert "server_time" in data

    # 4. Create new appeal and check badges reflect it
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    appeal = Appeal(
        ticket_number="APP-BADGE-001",
        student_id=student.id,
        service_id=service.id,
        status=AppealStatus.NEW,
        subject="Badge sinov arizasi",
        message="Ariza matni",
        created_at=now,
        earned_kpi_points=service.kpi_points
    )
    test_db.add(appeal)

    # Create today's appointment
    appt = Appointment(
        ticket_code="TALON-BADGE-1",
        student_id=student.id,
        service_id=service.id,
        window_number="1-darcha",
        appointment_date=today_str,
        time_slot="09:00 - 09:15",
        status=AppointmentStatus.BOOKED,
        created_at=now
    )
    test_db.add(appt)
    await test_db.commit()
    await test_db.refresh(appeal)

    head_res = await client.get("/api/v1/appeals/live-badges", headers={"Authorization": f"Bearer {head_token}"})
    assert head_res.status_code == 200
    head_data = head_res.json()

    assert head_data["new_appeals"] >= 1
    assert head_data["today_waiting_appointments"] >= 1
    assert head_data["last_appeal_id"] == appeal.id
