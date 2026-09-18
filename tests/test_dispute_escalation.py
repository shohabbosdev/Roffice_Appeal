import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import create_token_for_user
from app.models import UserRole, AppealStatus


async def test_dispute_escalation_to_head_and_prorektor(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    head = seed_test_data["head"]
    prorektor = seed_test_data["prorektor"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    prorektor_token = create_token_for_user(prorektor.id, UserRole.VICE_RECTOR)

    # 1. Student creates appeal
    create_resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "subject": "Diplom ilovasidagi fan bahosi",
            "message": "Fan bahosi reyting qaydnomasiga mos emas."
        }
    )
    appeal_id = create_resp.json()["id"]

    # 2. Staff resolves appeal
    await client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"resolution_text": "Baho HEMIS bo'yicha to'g'ri qo'yilgan."}
    )

    # 3. Student disputes resolution ("Hal bo'lmadi" - Tier 2)
    dispute_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/dispute",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"dispute_reason": "Vedomost asl nusxasidagi imzo bilan tizimdagi baho farq qilmoqda."}
    )
    assert dispute_resp.status_code == 200
    dispute_data = dispute_resp.json()
    assert dispute_data["status"] == AppealStatus.DISPUTED.value
    assert dispute_data["dispute_reason"] is not None

    # 4. Office Head investigates and escalates to Vice-Rector (Tier 3)
    escalate_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/escalate-prorektor",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"head_note": "Fakultet dekanati va kafedra xulosasi o'rganildi, yakuniy qaror talab etiladi."}
    )
    assert escalate_resp.status_code == 200
    assert escalate_resp.json()["status"] == AppealStatus.ESCALATED_PROREKTOR.value

    # 5. Vice-Rector makes final binding resolution
    prorektor_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/prorektor-decision",
        headers={"Authorization": f"Bearer {prorektor_token}"},
        json={"final_decision": "Komissiya xulosasiga asosan baho qayta hisoblansin va vedomost to'g'rilansin."}
    )
    assert prorektor_resp.status_code == 200
    final_data = prorektor_resp.json()
    assert final_data["status"] == AppealStatus.COMPLETED.value
    assert "[Prorektorning yakuniy qarori]" in final_data["resolution_text"]


async def test_reassign_ping_pong_prevention(client: AsyncClient, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    staff2 = seed_test_data["staff2"]
    head = seed_test_data["head"]
    service = seed_test_data["service"]

    student_token = create_token_for_user(student.id, UserRole.STUDENT)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)
    staff2_token = create_token_for_user(staff2.id, UserRole.BACK_STAFF)
    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)

    # 1. Create appeal
    create_resp = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "service_id": service.id,
            "subject": "Ping-pong tekshiruvi",
            "message": "Reassign limitini tekshirish."
        }
    )
    appeal_id = create_resp.json()["id"]

    # 2. Head assigns to Staff 1
    await client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"staff_id": staff.id}
    )

    # 3. Staff 1 reassigns to Staff 2 (1st reassign: permitted)
    reassign1_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/reassign",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"new_staff_id": staff2.id, "reason": "Mening soham emas"}
    )
    assert reassign1_resp.status_code == 200
    assert reassign1_resp.json()["status"] == AppealStatus.ASSIGNED.value
    assert reassign1_resp.json()["assigned_staff_id"] == staff2.id

    # 4. Staff 2 attempts to reassign again (Exceeds limit -> locks to Office Head!)
    reassign2_resp = await client.post(
        f"/api/v1/appeals/{appeal_id}/reassign",
        headers={"Authorization": f"Bearer {staff2_token}"},
        json={"new_staff_id": staff.id, "reason": "Men ham qaray olmayman"}
    )
    assert reassign2_resp.status_code == 200
    lock_data = reassign2_resp.json()
    assert lock_data["status"] == AppealStatus.ESCALATED_HEAD.value
    assert lock_data["assigned_staff_id"] is None
