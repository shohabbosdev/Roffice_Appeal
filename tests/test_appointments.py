import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, AppointmentStatus
from app.services.kpi_service import KPIService


async def test_appointment_booking_and_completion(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # 1. Check available slots
    slots_resp = await client.get(
        f"/api/v1/appointments/available-slots?appointment_date=2026-09-22&service_id={service.id}"
    )
    assert slots_resp.status_code == 200
    available_slots = slots_resp.json()
    assert "09:00 - 09:15" in available_slots
    assert "10:15 - 10:30" in available_slots
    # Ensure lunch slots (13:00-14:00) are NOT present
    for slot in available_slots:
        assert not slot.startswith("13:")

    # 2. Student books an appointment
    book_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "10:15 - 10:30"
        }
    )
    assert book_resp.status_code == 201
    apt_data = book_resp.json()
    apt_id = apt_data["id"]
    assert apt_data["status"] == AppointmentStatus.BOOKED.value
    assert apt_data["ticket_code"].startswith("TALON-")
    assert "1-darcha" in apt_data["window_number"]

    # 3. Double-booking prevention
    dup_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "10:15 - 10:30"
        }
    )
    assert dup_resp.status_code == 409
    assert "allaqachon band qilingan" in dup_resp.json()["detail"]

    # 4. Check that slot is no longer in available list
    slots_after_resp = await client.get(
        f"/api/v1/appointments/available-slots?appointment_date=2026-09-22&service_id={service.id}"
    )
    assert "10:15 - 10:30" not in slots_after_resp.json()

    # 5. Student arrives and checks in
    checkin_resp = await client.post(
        f"/api/v1/appointments/{apt_id}/check-in",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert checkin_resp.status_code == 200
    assert checkin_resp.json()["status"] == AppointmentStatus.CHECKED_IN.value

    # 6. Staff completes in-person consultation
    complete_resp = await client.post(
        f"/api/v1/appointments/{apt_id}/complete",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"notes": "Talaba shaxsan keldi, ma'lumotnoma muhr bosib topshirildi."}
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == AppointmentStatus.COMPLETED.value
    assert complete_resp.json()["completed_at"] is not None

    # 7. Verify staff received KPI points for in-person appointment
    kpi = await KPIService.get_or_create_monthly_target(test_db, staff.id, "2026-09")
    assert kpi.total_appointments_completed == 1
    assert kpi.completed_points == service.kpi_points
