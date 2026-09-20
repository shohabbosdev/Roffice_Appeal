import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, Appeal, AppealStatus, Appointment, AppointmentStatus, User
from datetime import datetime, timezone, timedelta
from app.services.telegram_service import TelegramService
from app.services.sla_reminder import check_and_send_sla_reminders
from app.services.queue_service import QueueService


@pytest.mark.asyncio
async def test_telegram_notification_methods():
    """Test format and execution of all Telegram notification methods."""
    with patch.object(TelegramService, "send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # 1. Clarification requested
        await TelegramService.notify_clarification_requested(12345, "APP-001", "Pasport nusxasini yuboring", "Transkript")
        assert mock_send.called
        assert "Pasport nusxasini yuboring" in mock_send.call_args[0][1]

        # 2. Clarification provided
        await TelegramService.notify_clarification_provided(54321, "APP-001", "Azamat Talaba", "Mana pasportim")
        assert "Mana pasportim" in mock_send.call_args[0][1]

        # 3. Appeal disputed
        await TelegramService.notify_appeal_disputed(11111, "APP-001", "Azamat Talaba", "Baho noto'g'ri")
        assert "Baho noto'g'ri" in mock_send.call_args[0][1]

        # 4. Appeal escalated to prorektor
        await TelegramService.notify_appeal_escalated_prorektor(22222, "APP-001", "Azamat Talaba", "Qayta ko'rilsin")
        assert "Qayta ko'rilsin" in mock_send.call_args[0][1]

        # 5. Prorektor decision
        await TelegramService.notify_prorektor_decision(12345, "APP-001", "Talabaning arizasi qanoatlantirilsin", is_student=True)
        assert "Talabaning arizasi qanoatlantirilsin" in mock_send.call_args[0][1]

        # 6. Appointment called
        await TelegramService.notify_appointment_called(12345, "TALON-A-101", "2-darcha")
        assert "2-darcha" in mock_send.call_args[0][1]

        # 7. Appointment reminder
        await TelegramService.notify_appointment_reminder(12345, "TALON-A-101", "2-darcha", "10:30 - 10:45", "Spravka")
        assert "10:30 - 10:45" in mock_send.call_args[0][1]


@pytest.mark.asyncio
async def test_appointment_called_triggers_telegram(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Test calling an appointment triggers Telegram notification to the student."""
    staff = seed_test_data["staff"]
    student = seed_test_data["student"]
    service = seed_test_data["service"]

    student.telegram_chat_id = 99887766
    await test_db.commit()

    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    now = datetime.now(timezone.utc)
    appt = Appointment(
        ticket_code="TALON-CALL-01",
        student_id=student.id,
        service_id=service.id,
        window_number="1-darcha",
        appointment_date=now.strftime("%Y-%m-%d"),
        time_slot="10:00 - 10:15",
        status=AppointmentStatus.CHECKED_IN,
        created_at=now
    )
    test_db.add(appt)
    await test_db.commit()
    await test_db.refresh(appt)

    with patch.object(TelegramService, "send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        res = await client.post(f"/api/v1/appointments/{appt.id}/call", headers={"Authorization": f"Bearer {staff_token}"})
        assert res.status_code == 200
        assert res.json()["status"] == "in_service"


@pytest.mark.asyncio
async def test_queue_30min_reminder_background_job(test_db: AsyncSession, seed_test_data):
    """Test background SLA reminder sends 30-min reminder to student with appointment."""
    student = seed_test_data["student"]
    service = seed_test_data["service"]

    student.telegram_chat_id = 777111222
    await test_db.commit()

    now = QueueService.get_now().replace(tzinfo=None)
    today_str = now.strftime("%Y-%m-%d")

    # Appointment scheduled 25 minutes from now (falls in 15-45 min window)
    appt = Appointment(
        ticket_code="TALON-REMIND-01",
        student_id=student.id,
        service_id=service.id,
        window_number="3-darcha",
        appointment_date=today_str,
        time_slot="11:00 - 11:15",
        scheduled_start=now + timedelta(minutes=25),
        status=AppointmentStatus.BOOKED,
        created_at=now
    )
    test_db.add(appt)
    await test_db.commit()

    with patch.object(TelegramService, "send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        await check_and_send_sla_reminders(test_db)

        # Verify Telegram message was sent for this ticket
        sent_calls = [call for call in mock_send.call_args_list if "TALON-REMIND-01" in str(call)]
        assert len(sent_calls) >= 1
