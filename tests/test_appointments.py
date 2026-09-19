import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import User, UserRole, AppointmentStatus
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

    # 3. Anti-Abuse: Same student tries to book another slot on the same date for the same service (400)
    same_student_dup = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "10:30 - 10:45"
        }
    )
    assert same_student_dup.status_code == 400
    assert "allaqachon faol navbat taloni mavjud" in same_student_dup.json()["detail"]

    # 4. Double-booking prevention: Another student tries to book the EXACT same slot (409)
    other_student = User(
        username="other_student_test",
        hashed_password="hashed_pass",
        full_name="Boshqa Talaba",
        role=UserRole.STUDENT,
        is_active=True
    )
    test_db.add(other_student)
    await test_db.commit()
    other_token = create_token_for_user(other_student.id, UserRole.STUDENT)

    dup_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "10:15 - 10:30"
        }
    )
    assert dup_resp.status_code == 409
    assert "allaqachon band qilingan" in dup_resp.json()["detail"]

    # 5. Check that slot is no longer in available list
    slots_after_resp = await client.get(
        f"/api/v1/appointments/available-slots?appointment_date=2026-09-22&service_id={service.id}"
    )
    assert "10:15 - 10:30" not in slots_after_resp.json()

    # 6. Student arrives and checks in
    checkin_resp = await client.post(
        f"/api/v1/appointments/{apt_id}/check-in",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert checkin_resp.status_code == 200
    assert checkin_resp.json()["status"] == AppointmentStatus.CHECKED_IN.value

    # 7. Staff completes in-person consultation
    complete_resp = await client.post(
        f"/api/v1/appointments/{apt_id}/complete",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"notes": "Talaba shaxsan keldi, ma'lumotnoma muhr bosib topshirildi."}
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == AppointmentStatus.COMPLETED.value
    assert complete_resp.json()["completed_at"] is not None

    # 8. Verify staff received KPI points for in-person appointment
    kpi = await KPIService.get_or_create_monthly_target(test_db, staff.id, "2026-09")
    assert kpi.total_appointments_completed == 1
    assert kpi.completed_points == service.kpi_points

    # 9. Test appointment cancellation flow
    new_apt_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-23",
            "time_slot": "11:00 - 11:15"
        }
    )
    assert new_apt_resp.status_code == 201
    new_apt_id = new_apt_resp.json()["id"]

    cancel_resp = await client.post(
        f"/api/v1/appointments/{new_apt_id}/cancel",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == AppointmentStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_today_and_my_appointments_endpoints(client: AsyncClient, test_db: AsyncSession, seed_test_data: dict):
    """GET /today, GET /my va DELETE /appointments/{id} endpointlarini sinovdan o'tkazish."""
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # 1. GET /today - dastlab bo'sh
    resp_today = await client.get(
        "/api/v1/appointments/today",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert resp_today.status_code == 200
    assert isinstance(resp_today.json(), list)

    # 2. GET /my - talabaning talonlari
    resp_my = await client.get(
        "/api/v1/appointments/my",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert resp_my.status_code == 200
    assert isinstance(resp_my.json(), list)

    # 3. Yangi navbat olamiz va DELETE orqali bekor qilamiz
    book_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-24",
            "time_slot": "14:15 - 14:30"
        }
    )
    assert book_resp.status_code == 201
    apt_id = book_resp.json()["id"]

    # DELETE /appointments/{id}
    del_resp = await client.delete(
        f"/api/v1/appointments/{apt_id}",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "cancelled"


