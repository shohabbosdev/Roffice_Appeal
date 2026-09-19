import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from tests.conftest import create_token_for_user
from app.models import UserRole, AppointmentStatus


@pytest.mark.asyncio
async def test_live_queue_board_full_flow(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    std_headers = {"Authorization": f"Bearer {student_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    today_str = date.today().strftime("%Y-%m-%d")

    # 1. Check /queue-board and /display HTML endpoints
    qb_res = await client.get("/queue-board")
    assert qb_res.status_code == 200
    assert "Jonli navbat tablosining ekrani" in qb_res.text

    disp_res = await client.get("/display")
    assert disp_res.status_code == 200
    assert "Jonli navbat tablosining ekrani" in disp_res.text

    # 2. Check public live-board API before booking
    lb_res = await client.get("/api/v1/appointments/live-board")
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert "today_date" in lb_data
    assert "stats" in lb_data
    assert "waiting_queue" in lb_data

    # 3. Create appointment for today
    from app.models import Appointment
    apt = Appointment(
        ticket_code="TALON-A-101",
        student_id=student.id,
        service_id=service.id,
        window_number="1-darcha",
        appointment_date=today_str,
        time_slot="14:00 - 14:15",
        status=AppointmentStatus.BOOKED,
        earned_kpi_points=service.kpi_points
    )
    test_db.add(apt)
    await test_db.commit()
    await test_db.refresh(apt)
    apt_id = apt.id
    ticket_code = apt.ticket_code

    # 4. Student arrives at office and checks in
    checkin_res = await client.post(f"/api/v1/appointments/{apt_id}/check-in", headers=std_headers)
    assert checkin_res.status_code == 200
    assert checkin_res.json()["status"] == AppointmentStatus.CHECKED_IN.value

    # 5. Check live board shows student in waiting_queue with is_arrived=True
    lb_res2 = await client.get("/api/v1/appointments/live-board")
    assert lb_res2.status_code == 200
    lb_data2 = lb_res2.json()
    matching_waiting = [w for w in lb_data2["waiting_queue"] if w["id"] == apt_id]
    assert len(matching_waiting) == 1
    assert matching_waiting[0]["is_arrived"] is True

    # 6. Staff / Operator calls student to window
    call_res = await client.post(f"/api/v1/appointments/{apt_id}/call", headers=staff_headers)
    assert call_res.status_code == 200
    called_data = call_res.json()
    assert called_data["status"] == AppointmentStatus.IN_SERVICE.value
    assert called_data["called_at"] is not None

    # 7. Check live board now shows student as latest_called and active_windows
    lb_res3 = await client.get("/api/v1/appointments/live-board")
    assert lb_res3.status_code == 200
    lb_data3 = lb_res3.json()
    assert lb_data3["latest_called"] is not None
    assert lb_data3["latest_called"]["ticket_code"] == ticket_code
    assert lb_data3["stats"]["in_service_count"] >= 1

    # 8. Staff completes appointment
    complete_res = await client.post(f"/api/v1/appointments/{apt_id}/complete", headers=staff_headers, json={
        "notes": "Talabaga darchada to'liq xizmat ko'rsatildi"
    })
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == AppointmentStatus.COMPLETED.value
    assert complete_res.json()["completed_at"] is not None
