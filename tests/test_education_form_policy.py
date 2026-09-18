import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserRole
from app.core.security import create_access_token, hash_password


def create_token_for_user(user_id: int, role: UserRole) -> str:
    return create_access_token(
        data={"sub": str(user_id), "role": role.value, "username": f"user_{user_id}"}
    )


@pytest.mark.anyio
async def test_dynamic_education_form_policy(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Admin/Boshliq ta'lim shakli cheklovini dinamik o'zgartirishi va talaba murojaatiga ta'siri."""
    head = seed_test_data["head"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    head_token = create_token_for_user(head.id, UserRole.OFFICE_HEAD)
    staff_token = create_token_for_user(staff.id, UserRole.FRONT_STAFF)

    # Kunduzgi talaba
    kunduzgi_student = User(
        username="dynamic_kunduzgi_student",
        hashed_password=hash_password("Pass123!"),
        full_name="Dinamik Kunduzgi Talaba",
        role=UserRole.STUDENT,
        hemis_student_id="HEMIS-DYN-01",
        education_form="Kunduzgi"
    )
    test_db.add(kunduzgi_student)
    await test_db.commit()
    await test_db.refresh(kunduzgi_student)
    student_token = create_token_for_user(kunduzgi_student.id, UserRole.STUDENT)

    # 1. Standart holatda siyosatni o'qish (Kunduzgi taqiqlangan)
    resp = await client.get("/api/v1/appeals/policy/education-forms")
    assert resp.status_code == 200
    data = resp.json()
    assert "kunduzgi" not in data["allowed_forms"]
    assert "sirtqi" in data["allowed_forms"]

    # 2. Xodim siyosatni o'zgartira olmaydi (403)
    resp_staff = await client.post(
        "/api/v1/appeals/policy/education-forms",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"allowed_forms": ["kunduzgi", "sirtqi"]}
    )
    assert resp_staff.status_code == 403

    # 3. Kunduzgi talaba murojaat yo'llashga urinadi -> 403
    resp_appeal = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"service_id": service.id, "subject": "Test", "message": "Test"}
    )
    assert resp_appeal.status_code == 403

    # 4. Boshliq kunduzgi ta'lim shakliga ham onlayn ruxsat beradi
    resp_update = await client.post(
        "/api/v1/appeals/policy/education-forms",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"allowed_forms": ["kunduzgi", "sirtqi", "masofaviy"]}
    )
    assert resp_update.status_code == 200
    assert "kunduzgi" in resp_update.json()["allowed_forms"]

    # 5. Endi kunduzgi talaba murojaat yo'llay oladi! (201 Created)
    resp_allowed = await client.post(
        "/api/v1/appeals",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"service_id": service.id, "subject": "Muvaffaqiyatli murojaat", "message": "Onlayn ruxsat berildi"}
    )
    assert resp_allowed.status_code == 201
    assert resp_allowed.json()["subject"] == "Muvaffaqiyatli murojaat"

    # 6. Boshliq kunduzgi ta'limni qayta cheklaydi (standart holatga qaytarish)
    resp_reset = await client.post(
        "/api/v1/appeals/policy/education-forms",
        headers={"Authorization": f"Bearer {head_token}"},
        json={"allowed_forms": ["sirtqi", "masofaviy", "kechki"]}
    )
    assert resp_reset.status_code == 200
    assert "kunduzgi" not in resp_reset.json()["allowed_forms"]
