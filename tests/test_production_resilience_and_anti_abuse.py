import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import Appointment, AppointmentStatus, Service, User, AppealStatus
from app.services.hemis_client import HemisClient
from app.services.queue_service import QueueService
from app.services.appeal_service import AppealService
from app.services.backup_service import BackupService, BACKUP_DIR
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_hemis_ttl_cache():
    """HEMIS API kesh tizimi TTL in-memory cache ishlashini tekshirish."""
    HemisClient._profile_cache.clear()
    
    mock_response = {
        "id": "HEMIS-12345",
        "full_name": "TEST TALABA",
        "student_id_number": "401251200099"
    }

    token_str = "test_hemis_token_xyz"
    # Keshga yozish
    HemisClient._profile_cache[token_str] = (datetime.now(timezone.utc), mock_response)
    
    # Keshlangan qiymatni tekshirish
    cached = HemisClient._profile_cache.get(token_str)
    assert cached is not None
    assert cached[1]["full_name"] == "TEST TALABA"


@pytest.mark.asyncio
async def test_queue_daily_ticket_limit(test_db: AsyncSession, seed_test_data):
    """Bir talabaning bir kunda ko'pi bilan 3 ta talon olishi chegarasini tekshirish."""
    student = seed_test_data["student"]
    service = seed_test_data["service"]
    dept = seed_test_data["dept"]

    # 2 ta qo'shimcha xizmat yaratamiz
    svc2 = Service(
        code="SVC_TEST_2",
        title="Sinov xizmati 2",
        department_id=dept.id,
        kpi_points=1,
        sla_hours=24
    )
    svc3 = Service(
        code="SVC_TEST_3",
        title="Sinov xizmati 3",
        department_id=dept.id,
        kpi_points=1,
        sla_hours=24
    )
    svc4 = Service(
        code="SVC_TEST_4",
        title="Sinov xizmati 4",
        department_id=dept.id,
        kpi_points=1,
        sla_hours=24
    )
    test_db.add_all([svc2, svc3, svc4])
    await test_db.flush()

    workday_dt = datetime(2026, 9, 21, 8, 0, tzinfo=QueueService.TASHKENT_TZ)
    workday_str = workday_dt.strftime("%Y-%m-%d")

    with patch.object(QueueService, "get_now", return_value=workday_dt), \
         patch.object(QueueService, "is_working_day", return_value=(True, None)):

        # 1, 2 va 3-talonlar muvaffaqiyatli olinadi
        app1 = await QueueService.book_appointment(
            db=test_db,
            student_id=student.id,
            service_id=service.id,
            appointment_date=workday_str,
            time_slot="09:00-09:30"
        )
        assert app1.ticket_code is not None

        app2 = await QueueService.book_appointment(
            db=test_db,
            student_id=student.id,
            service_id=svc2.id,
            appointment_date=workday_str,
            time_slot="10:00-10:30"
        )
        assert app2.ticket_code is not None

        app3 = await QueueService.book_appointment(
            db=test_db,
            student_id=student.id,
            service_id=svc3.id,
            appointment_date=workday_str,
            time_slot="11:00-11:30"
        )
        assert app3.ticket_code is not None

        # 4-talon olinayotganda 400 xatolik va kunlik cheklov qaytishi shart
        with pytest.raises(HTTPException) as exc_info:
            await QueueService.book_appointment(
                db=test_db,
                student_id=student.id,
                service_id=svc4.id,
                appointment_date=workday_str,
                time_slot="14:00-14:30"
            )
        assert exc_info.value.status_code == 400
        assert "ko'pi bilan 3 ta navbat taloni" in exc_info.value.detail


@pytest.mark.asyncio
async def test_queue_no_show_cooldown(test_db: AsyncSession, seed_test_data):
    """So'nggi 7 kunda 3 marta No-Show bo'lgan talabani 3 kunlik cheklovga tushishini tekshirish."""
    student = seed_test_data["student"]
    service = seed_test_data["service"]
    workday_dt = datetime(2026, 9, 21, 8, 0, tzinfo=QueueService.TASHKENT_TZ)
    workday_str = workday_dt.strftime("%Y-%m-%d")

    # Oldingi 3 kunda kelmagan (NO_SHOW) 3 ta navbat yaratamiz
    for i in range(1, 4):
        past_date = (workday_dt.date() - timedelta(days=i)).strftime("%Y-%m-%d")
        ns_appt = Appointment(
            ticket_code=f"T-NS-{i}",
            student_id=student.id,
            service_id=service.id,
            window_number="1-darcha",
            appointment_date=past_date,
            time_slot="10:00-10:30",
            status=AppointmentStatus.NO_SHOW
        )
        test_db.add(ns_appt)
    await test_db.flush()

    with patch.object(QueueService, "get_now", return_value=workday_dt), \
         patch.object(QueueService, "is_working_day", return_value=(True, None)):
        # Yangi navbat olishga uringanda 403 xatolik va intizomiy cheklov berilishi shart
        with pytest.raises(HTTPException) as exc_info:
            await QueueService.book_appointment(
                db=test_db,
                student_id=student.id,
                service_id=service.id,
                appointment_date=workday_str,
                time_slot="15:00-15:30"
            )
        assert exc_info.value.status_code == 403
        assert "kelmagansiz (No-Show)" in exc_info.value.detail


@pytest.mark.asyncio
async def test_student_cancel_appeal_endpoint(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Talaba o'zining NEW holatidagi arizasini bekor qila olishi va ijrodagisini bekor qilolmasligi."""
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, student.role)
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Yangi murojaat yaratamiz
    appeal = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="Xato ariza",
        message="Men xato topshirgan edim, bekor qilmoqchiman."
    )

    # 2. Bekor qilish endpointi
    resp = await client.post(
        f"/api/v1/appeals/{appeal.id}/cancel",
        json={"reason": "O'zim noto'g'ri ma'lumot kiritibman"},
        headers=student_headers
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "cancelled"
    assert "Talaba tomonidan bekor qilindi" in res_data["resolution_text"]

    # 3. Agar xodimga biriktirilgan arizani bekor qilmoqchi bo'lsa xato qaytishi kerak
    appeal2 = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="Ijrodagi ariza",
        message="Tekshiruv uchun"
    )
    await AppealService.assign_appeal(
        db=test_db,
        appeal_id=appeal2.id,
        staff_id=staff.id,
        assigned_by_user_id=seed_test_data["head"].id
    )

    resp_fail = await client.post(
        f"/api/v1/appeals/{appeal2.id}/cancel",
        json={"reason": "Endi bekor qilmoqchiman"},
        headers=student_headers
    )
    assert resp_fail.status_code == 400
    assert "Ushbu murojaatni bekor qilib bo'lmaydi" in resp_fail.json()["detail"]


@pytest.mark.asyncio
async def test_backup_retention_cleanup():
    """30 kundan oshgan eski zaxira nusxalarini diskdan tozalashni tekshirish."""
    BackupService.ensure_backup_dir()
    
    # 40 kun oldingi soxta zaxira fayl
    old_file = BACKUP_DIR / "backup_roffice_20250101_000000.tar.gz"
    old_file.write_text("dummy backup content")
    
    # Fayl mtime ini 40 kun oldinga suramiz
    forty_days_ago = (datetime.now(timezone.utc) - timedelta(days=40)).timestamp()
    import os
    os.utime(old_file, (forty_days_ago, forty_days_ago))

    deleted_count = BackupService.cleanup_old_backups(days=30)
    assert deleted_count >= 1
    assert not old_file.exists()


@pytest.mark.asyncio
async def test_weekly_audit_report_endpoint(client: AsyncClient, seed_test_data):
    """Haftalik audit statistikasi xulosasi endpointini tekshirish."""
    head = seed_test_data["head"]
    head_token = create_token_for_user(head.id, head.role)
    head_headers = {"Authorization": f"Bearer {head_token}"}

    resp = await client.get("/api/v1/audit-logs/weekly-summary", headers=head_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "total_audit_records" in data
    assert "actions_breakdown" in data
    assert "top_active_users" in data
    assert data["period"]["days"] == 7
