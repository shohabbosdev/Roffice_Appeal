import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Appointment, AppointmentStatus, User, UserRole, Service, Department
from app.services.queue_service import QueueService
from tests.conftest import create_token_for_user
from scripts.cleanup_mock_data import cleanup_mock_data, MOCK_STUDENT_USERNAMES


@pytest.mark.asyncio
async def test_yesterday_uncompleted_appointments_auto_expire_to_no_show(test_db: AsyncSession, seed_test_data):
    """Kechagi va o'tgan kunlardagi kelinmagan/yakunlanmagan barcha navbatlar yangi kunda avtomatik yopilishi shart."""
    service = seed_test_data["service"]
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]

    yesterday_str = (QueueService.get_now().date() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Kechagi BOOKED talon
    apt_booked = Appointment(
        student_id=student.id,
        service_id=service.id,
        ticket_code="TALON-YEST-BOOKED",
        appointment_date=yesterday_str,
        time_slot="10:00 - 10:15",
        window_number="1-darcha",
        status=AppointmentStatus.BOOKED
    )
    # 2. Kechagi CHECKED_IN talon
    apt_checked_in = Appointment(
        student_id=student.id,
        service_id=service.id,
        ticket_code="TALON-YEST-CHECKED",
        appointment_date=yesterday_str,
        time_slot="10:15 - 10:30",
        window_number="1-darcha",
        status=AppointmentStatus.CHECKED_IN
    )
    # 3. Kechagi xodim yakunlamagan IN_SERVICE talon
    apt_in_service = Appointment(
        student_id=student.id,
        service_id=service.id,
        staff_id=staff.id,
        ticket_code="TALON-YEST-INSERVICE",
        appointment_date=yesterday_str,
        time_slot="10:30 - 10:45",
        window_number="1-darcha",
        status=AppointmentStatus.IN_SERVICE
    )
    test_db.add_all([apt_booked, apt_checked_in, apt_in_service])
    await test_db.commit()

    # Avto-tozalashni chaqiramiz
    cleaned_count = await QueueService.auto_expire_no_show_appointments(test_db)
    assert cleaned_count >= 3

    await test_db.refresh(apt_booked)
    await test_db.refresh(apt_checked_in)
    await test_db.refresh(apt_in_service)

    # BOOKED va CHECKED_IN navbatlar NO_SHOW ga o'tgan bo'lishi shart
    assert apt_booked.status == AppointmentStatus.NO_SHOW
    assert "No-Show" in apt_booked.notes
    assert apt_checked_in.status == AppointmentStatus.NO_SHOW
    assert "No-Show" in apt_checked_in.notes

    # IN_SERVICE navbat esa COMPLETED qilib arxivlangan bo'lishi shart
    assert apt_in_service.status == AppointmentStatus.COMPLETED
    assert "Ish kuni tugagani sababli" in apt_in_service.notes


@pytest.mark.asyncio
async def test_today_appointments_api_triggers_auto_clean(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """/today yoki live-board chaqirilganda ham kechagi navbatlar avtomatik tozalanishi."""
    service = seed_test_data["service"]
    student = seed_test_data["student"]
    yesterday_str = (QueueService.get_now().date() - timedelta(days=2)).strftime("%Y-%m-%d")

    old_apt = Appointment(
        student_id=student.id,
        service_id=service.id,
        ticket_code="TALON-OLD-STALE",
        appointment_date=yesterday_str,
        time_slot="11:00 - 11:15",
        window_number="1-darcha",
        status=AppointmentStatus.BOOKED
    )
    test_db.add(old_apt)
    await test_db.commit()

    # /today ga so'rov yuboramiz
    token = create_token_for_user(student.id, UserRole.STUDENT)
    resp = await client.get("/api/v1/appointments/today", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Oldingi talon NO_SHOW ga o'tganligini tekshiramiz
    await test_db.refresh(old_apt)
    assert old_apt.status == AppointmentStatus.NO_SHOW


@pytest.mark.asyncio
async def test_cleanup_mock_data_script(test_db: AsyncSession):
    """scripts/cleanup_mock_data.py faqat mock talabalarni tozalashi va haqiqiy talabalarga tegmasligini tekshirish."""
    # Mock talaba yaratamiz
    mock_u = User(
        username="student_mock_temp",
        hashed_password="h",
        full_name="Mock Temp",
        role=UserRole.STUDENT,
        hemis_student_id="HEMIS-MOCK-TEMP"
    )
    # Haqiqiy talaba
    real_u = User(
        username="401251200032",
        hashed_password="h",
        full_name="Haqiqiy Talaba",
        role=UserRole.STUDENT,
        hemis_student_id="401251200032"
    )
    test_db.add_all([mock_u, real_u])
    await test_db.commit()

    # Tozalash skriptini chaqiramiz
    await cleanup_mock_data(test_db)

    # Bazadan tekshiramiz
    stmt_mock = select(User).where(User.username == "student_mock_temp")
    deleted_mock = (await test_db.execute(stmt_mock)).scalar_one_or_none()
    assert deleted_mock is None

    stmt_real = select(User).where(User.username == "401251200032")
    retained_real = (await test_db.execute(stmt_real)).scalar_one_or_none()
    assert retained_real is not None
    assert retained_real.full_name == "Haqiqiy Talaba"


def test_auth_no_mock_hemis_token():
    """app/api/v1/auth.py faylida mock-hemis-token matni qolmaganligi."""
    with open("app/api/v1/auth.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "mock-hemis-token" not in content


def test_static_html_no_fake_profile_defaults():
    """student.html va portal.html da fake fakultet va guruh fallbacklari olib tashlanganligi."""
    with open("app/static/student.html", "r", encoding="utf-8") as f:
        s_html = f.read()
    assert "Axborot texnologiyalari fakulteti" not in s_html

    with open("app/static/portal.html", "r", encoding="utf-8") as f:
        p_html = f.read()
    assert 'currentUser.group_name || "M07-25"' not in p_html
