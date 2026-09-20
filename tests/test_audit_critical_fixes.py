import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models import User, UserRole, Service, Department, Appointment, AppointmentStatus, Appeal, AppealStatus
from tests.conftest import create_token_for_user
from app.services.appeal_service import AppealService
from app.services.kpi_service import KPIService


@pytest.mark.asyncio
async def test_audit_fix_inactive_user_forbidden_403(client: AsyncClient, test_db: AsyncSession):
    """6-kamchilik testi: Bloklangan yoki nofaol foydalanuvchi tizimga murojaat qilganda 403 Forbidden olishi shart."""
    inactive_user = User(
        username="inactive_student_test",
        hashed_password="hash",
        full_name="Nofaol Talaba",
        role=UserRole.STUDENT,
        is_active=False
    )
    test_db.add(inactive_user)
    await test_db.commit()

    token = create_token_for_user(inactive_user.id, UserRole.STUDENT)
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "faol emas yoki ma'muriyat tomonidan bloklangan" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_audit_fix_in_service_slot_cannot_be_double_booked(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """1-kamchilik testi: IN_SERVICE holatidagi talon vaqtini boshqa talaba qayta band qila olmasligi (409 Conflict)."""
    service = seed_test_data["service"]
    student1 = seed_test_data["student"]

    student2 = User(
        username="audit_stud_2",
        hashed_password="h",
        full_name="Audit Student 2",
        role=UserRole.STUDENT,
        is_active=True
    )
    test_db.add(student2)
    await test_db.commit()

    # Student 1 uchun IN_SERVICE holatidagi navbat yaratamiz
    in_service_apt = Appointment(
        student_id=student1.id,
        service_id=service.id,
        ticket_code="TALON-AUDIT-001",
        appointment_date="2026-09-22",
        time_slot="11:00 - 11:15",
        window_number="1-darcha",
        status=AppointmentStatus.IN_SERVICE
    )
    test_db.add(in_service_apt)
    await test_db.commit()

    token2 = create_token_for_user(student2.id, UserRole.STUDENT)
    dup_resp = await client.post(
        "/api/v1/appointments/book",
        headers={"Authorization": f"Bearer {token2}"},
        json={
            "service_id": service.id,
            "appointment_date": "2026-09-22",
            "time_slot": "11:00 - 11:15"
        }
    )
    assert dup_resp.status_code == 409
    assert "allaqachon band qilingan" in dup_resp.json()["detail"]


@pytest.mark.asyncio
async def test_audit_fix_auto_close_does_not_artificially_inflate_rating(test_db: AsyncSession, seed_test_data):
    """2-kamchilik testi: 72 soatlik avto-yopilish xodimning o'rtacha yulduzli reytingini buzmasligi (rating=None)."""
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    # Xodimning boshlang'ich KPI ko'rsatkichini olamiz va 4.25 ga o'rnatamiz
    kpi_before = await KPIService.get_or_create_monthly_target(test_db, staff.id, "2026-09")
    kpi_before.average_rating = 4.25
    await test_db.commit()

    # 4 kun oldin muddati o'tgan (confirmation_deadline_at) RESOLVED holatidagi murojaat
    four_days_ago = datetime.now(timezone.utc) - timedelta(hours=96)
    appeal = Appeal(
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        ticket_number="APP-AUDIT-AUTOCLOSE",
        subject="Muddati o'tgan murojaat",
        message="Talaba 72 soat davomida baholamagan murojaat",
        status=AppealStatus.RESOLVED,
        resolved_at=four_days_ago,
        confirmation_deadline_at=four_days_ago
    )
    test_db.add(appeal)
    await test_db.commit()

    # Avto-yopilishni chaqiramiz
    closed_count = await AppealService.auto_close_expired(test_db)
    assert closed_count >= 1

    await test_db.refresh(appeal)
    assert appeal.status == AppealStatus.AUTO_CLOSED
    # Rating sun'iy 5 bo'lmasligi, None bo'lib qolishi shart
    assert appeal.rating is None

    # KPI ni tekshiramiz: rating None bo'lgani sababli average_rating 4.25 bo'lib saqlanadi, sun'iy 5.0 bo'lib ketmaydi!
    kpi_after = await KPIService.get_or_create_monthly_target(test_db, staff.id, "2026-09")
    assert kpi_after.average_rating == 4.25
    assert kpi_after.total_appeals_completed >= 1


def test_audit_fix_docker_compose_has_backups_volume():
    """3-kamchilik testi: docker-compose.yml faylida backups papkasi ulanishi shart."""
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "- ./backups:/app/backups" in content


def test_audit_fix_portal_html_no_hardcoded_student_creds():
    """5-kamchilik testi: portal.html da qattiq kodlangan test login/parollar va tugmalar bo'lmasligi shart."""
    with open("app/static/portal.html", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Zoxidjon (kunduzgi)" not in content
    assert "Azamat (sirtqi)" not in content
    assert "switchDemoUser" not in content
    assert "(Zetmax0011)" not in content


def test_audit_fix_telegram_poller_status_handling():
    """4-kamchilik testi: telegram_bot.py da 409 Conflict va 429 Rate Limit backoff bilan himoyalangan bo'lishi shart."""
    with open("app/services/telegram_bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "resp.status_code == 409" in content
    assert "resp.status_code == 429" in content


def test_audit_fix_queue_board_global_audio_unlock():
    """7-kamchilik testi: queue_board.html da butun ekranga birinchi bosishda Web Audio unlock tinglovchisi mavjudligi."""
    with open("app/static/queue_board.html", "r", encoding="utf-8") as f:
        content = f.read()
    assert "touchstart" in content
    assert "initAudioContext()" in content
    assert "audio-unlock-banner" in content
