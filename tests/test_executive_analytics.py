import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, Appeal, AppealStatus
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_executive_analytics_flow(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    head = seed_test_data["head"]
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # 1. Non-executive user (Student) gets 403 Forbidden
    student_res = await client.get("/api/v1/appeals/analytics/executive", headers={"Authorization": f"Bearer {student_token}"})
    assert student_res.status_code == 403

    # 2. Staff user gets 403 Forbidden
    staff_res = await client.get("/api/v1/appeals/analytics/executive", headers={"Authorization": f"Bearer {staff_token}"})
    assert staff_res.status_code == 403

    # 3. Create test appeals in test_db with different statuses, faculties, ratings
    now = datetime.now(timezone.utc)
    student.faculty = "Iqtisodiyot va axborot texnologiyalari fakulteti"
    await test_db.commit()

    appeal1 = Appeal(
        ticket_number="APP-TEST-001",
        student_id=student.id,
        service_id=service.id,
        status=AppealStatus.RESOLVED,
        subject="Sinov arizasi 1",
        message="Ariza matni",
        created_at=now - timedelta(hours=5),
        resolved_at=now - timedelta(hours=1),
        sla_deadline_at=now + timedelta(hours=20),
        rating=5,
        rating_comment="A'lo darajada!",
        earned_kpi_points=service.kpi_points
    )
    appeal2 = Appeal(
        ticket_number="APP-TEST-002",
        student_id=student.id,
        service_id=service.id,
        status=AppealStatus.IN_PROGRESS,
        subject="Sinov arizasi 2",
        message="Ariza matni 2",
        created_at=now - timedelta(hours=2),
        sla_deadline_at=now + timedelta(hours=24),
        earned_kpi_points=service.kpi_points
    )
    appeal3 = Appeal(
        ticket_number="APP-TEST-003",
        student_id=student.id,
        service_id=service.id,
        status=AppealStatus.DISPUTED,
        subject="Sinov arizasi 3",
        message="Ariza matni 3",
        created_at=now - timedelta(hours=8),
        resolved_at=now - timedelta(hours=4),
        sla_deadline_at=now + timedelta(hours=12),
        rating=2,
        rating_comment="Qoniqarsiz",
        dispute_reason="Muddati cho'zildi",
        earned_kpi_points=service.kpi_points
    )
    test_db.add_all([appeal1, appeal2, appeal3])
    await test_db.commit()

    # 4. Office Head accesses executive analytics
    head_res = await client.get("/api/v1/appeals/analytics/executive?period=all", headers={"Authorization": f"Bearer {head_token}"})
    assert head_res.status_code == 200
    data = head_res.json()

    # Verify summary
    summary = data["summary"]
    assert summary["total_appeals"] >= 3
    assert summary["completed_appeals"] >= 1
    assert summary["in_progress_appeals"] >= 1
    assert summary["disputed_appeals"] >= 1
    assert summary["sla_compliance_percent"] > 0
    assert summary["avg_student_rating"] > 0

    # Verify by_faculty
    by_faculty = data["by_faculty"]
    assert len(by_faculty) >= 1
    fac_names = [f["faculty"] for f in by_faculty]
    assert "Iqtisodiyot va axborot texnologiyalari fakulteti" in fac_names

    # Verify top_services
    top_services = data["top_services"]
    assert len(top_services) >= 1
    assert top_services[0]["title"] == service.title
    assert top_services[0]["percentage"] > 0

    # Verify trends
    trends = data["trends"]
    assert len(trends) == 14
