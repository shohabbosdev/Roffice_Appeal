import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole


async def test_holiday_calendar_management(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    head = seed_test_data["head"]
    student = seed_test_data["student"]

    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    student_token = create_token_for_user(student.id, UserRole.STUDENT)

    # 1. Student cannot add holidays (403 Forbidden)
    student_add_resp = await client.post(
        "/api/v1/calendar/holidays",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"holiday_date": "2026-11-18", "title": "O'zbekiston bayrog'i kuni", "is_working_day": False}
    )
    assert student_add_resp.status_code == 403

    # 2. Office Head adds a new holiday
    head_add_resp = await client.post(
        "/api/v1/calendar/holidays",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"holiday_date": "2026-11-18", "title": "O'zbekiston bayrog'i kuni", "is_working_day": False}
    )
    assert head_add_resp.status_code == 201
    holiday_data = head_add_resp.json()
    holiday_id = holiday_data["id"]
    assert holiday_data["holiday_date"] == "2026-11-18"
    assert holiday_data["title"] == "O'zbekiston bayrog'i kuni"

    # 3. Duplicate date conflict check (409 Conflict)
    dup_resp = await client.post(
        "/api/v1/calendar/holidays",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"holiday_date": "2026-11-18", "title": "Takroriy sana"}
    )
    assert dup_resp.status_code == 409

    # 4. List holidays
    list_resp = await client.get("/api/v1/calendar/holidays")
    assert list_resp.status_code == 200
    holidays = list_resp.json()
    assert any(h["holiday_date"] == "2026-11-18" for h in holidays)

    # 5. Delete holiday
    delete_resp = await client.delete(
        f"/api/v1/calendar/holidays/{holiday_id}",
        headers={"Authorization": f"Bearer {head_token}"}
    )
    assert delete_resp.status_code == 204

    # 6. Verify holiday is deleted
    list_after = await client.get("/api/v1/calendar/holidays")
    assert not any(h["id"] == holiday_id for h in list_after.json())
