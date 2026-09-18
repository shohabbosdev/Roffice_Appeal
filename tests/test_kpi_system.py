import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.kpi_service import KPIService
from tests.conftest import create_token_for_user
from app.models import UserRole


async def test_kpi_get_or_create_target(test_db: AsyncSession, seed_test_data):
    staff = seed_test_data["staff"]
    kpi = await KPIService.get_or_create_monthly_target(test_db, staff.id, period="2026-10")

    assert kpi.employee_id == staff.id
    assert kpi.target_points == 150
    assert kpi.completed_points == 0
    assert kpi.penalty_points == 0
    assert kpi.average_rating == 5.0
    assert kpi.kpi_percentage == 0.0


async def test_kpi_accumulation_and_rating_multiplier(test_db: AsyncSession, seed_test_data):
    staff = seed_test_data["staff"]

    # 1. First appeal completed: 10 points, rating 5
    kpi1 = await KPIService.record_completed_service(
        db=test_db,
        employee_id=staff.id,
        kpi_points=10,
        rating=5,
        is_appointment=False
    )
    assert kpi1.completed_points == 10
    assert kpi1.total_appeals_completed == 1
    assert kpi1.average_rating == 5.0
    # (10 / 150) * 1.0 * 100 = 6.7%
    assert kpi1.kpi_percentage == 6.7

    # 2. Second service (appointment): 20 points, rating 4
    kpi2 = await KPIService.record_completed_service(
        db=test_db,
        employee_id=staff.id,
        kpi_points=20,
        rating=4,
        is_appointment=True
    )
    assert kpi2.completed_points == 30
    assert kpi2.total_appeals_completed == 1
    assert kpi2.total_appointments_completed == 1
    # Average rating: (5 + 4) / 2 = 4.5
    assert kpi2.average_rating == 4.5
    # Rating factor: 4.5 / 5.0 = 0.90
    # KPI %: (30 / 150) * 0.90 * 100 = 18.0%
    assert kpi2.kpi_percentage == 18.0


async def test_kpi_penalty_deduction(test_db: AsyncSession, seed_test_data):
    staff = seed_test_data["staff"]

    # Award 50 points with rating 5.0
    await KPIService.record_completed_service(
        db=test_db,
        employee_id=staff.id,
        kpi_points=50,
        rating=5,
        is_appointment=False
    )

    # Apply 5 points SLA penalty
    kpi_after_penalty = await KPIService.apply_penalty(
        db=test_db,
        employee_id=staff.id,
        penalty_points=5
    )
    assert kpi_after_penalty.penalty_points == 5
    # Net points = 50 - 5 = 45
    # KPI % = (45 / 150) * 1.0 * 100 = 30.0%
    assert kpi_after_penalty.kpi_percentage == 30.0


async def test_kpi_api_endpoints(client: AsyncClient, seed_test_data):
    staff = seed_test_data["staff"]
    head = seed_test_data["head"]

    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)

    # 1. Staff checks own KPI
    response = await client.get(
        "/api/v1/kpi/my?period=2026-09",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_points"] == 150
    assert data["employee_id"] == staff.id

    # 2. Office Head views overview of all employees
    overview_resp = await client.get(
        "/api/v1/kpi/overview?period=2026-09",
        headers={"Authorization": f"Bearer {head_token}"}
    )
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert isinstance(overview_data, list)
    assert len(overview_data) >= 1

    # 3. Office Head applies penalty via API
    penalize_resp = await client.post(
        "/api/v1/kpi/penalize",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"employee_id": staff.id, "penalty_points": 5, "reason": "SLA kechikishi"}
    )
    assert penalize_resp.status_code == 200
    assert penalize_resp.json()["penalty_points"] == 5
