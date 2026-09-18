import pytest
from datetime import datetime, timezone, timedelta
from app.services.queue_service import QueueService
from app.models import Service, Department, ResolutionMode, DepartmentType


@pytest.mark.asyncio
async def test_get_detailed_slots_past_and_today(test_db):
    """Bugungi kun va o'tib ketgan slotlar holatini tekshirish."""
    # 1. Department va Service yaratish
    dept = Department(name="Ro'yxatga olish sektori", code="REG_SECTOR", dept_type=DepartmentType.FRONT_OFFICE)
    test_db.add(dept)
    await test_db.flush()

    srv = Service(
        code="SRV_QUEUE_TEST",
        title="Diplom ilovasini olish",
        department_id=dept.id,
        resolution_mode=ResolutionMode.IN_PERSON_ONLY,
        kpi_points=1,
        sla_hours=24
    )
    test_db.add(srv)
    await test_db.commit()

    tashkent_tz = timezone(timedelta(hours=5))
    now = datetime.now(tashkent_tz)
    today_str = now.strftime("%Y-%m-%d")

    # Bugungi kun uchun detailed slotlarni olish
    res_today = await QueueService.get_detailed_slots(
        db=test_db,
        appointment_date=today_str,
        service_id=srv.id
    )

    assert res_today["date"] == today_str
    assert res_today["is_working_day"] is True
    assert "slots" in res_today
    assert len(res_today["slots"]) == len(QueueService.DEFAULT_SLOTS)

    # Har bir slotda to'g'ri maydonlar mavjudligini tekshirish
    for s in res_today["slots"]:
        assert "time_slot" in s
        assert "is_available" in s
        assert "status" in s
        assert s["status"] in ["available", "past", "booked"]


@pytest.mark.asyncio
async def test_get_detailed_slots_sunday_and_past_date(test_db):
    """Yakshanba va o'tib ketgan sanalarni tekshirish."""
    dept = Department(name="Maslahat sektori", code="ADV_SECTOR", dept_type=DepartmentType.FRONT_OFFICE)
    test_db.add(dept)
    await test_db.flush()

    srv = Service(
        code="SRV_SUN_TEST",
        title="Akademik maslahat",
        department_id=dept.id,
        resolution_mode=ResolutionMode.IN_PERSON_ONLY,
        kpi_points=1,
        sla_hours=24
    )
    test_db.add(srv)
    await test_db.commit()

    # Yakshanba: 2026-09-20 (Sunday)
    res_sunday = await QueueService.get_detailed_slots(
        db=test_db,
        appointment_date="2026-09-20",
        service_id=srv.id
    )
    assert res_sunday["is_working_day"] is False
    assert "Yakshanba" in res_sunday["message"]
    assert len(res_sunday["slots"]) == 0
