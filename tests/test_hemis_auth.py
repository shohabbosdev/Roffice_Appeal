import pytest
from httpx import AsyncClient
from app.services.hemis_client import HemisClient
from app.models import User, UserRole
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession


def test_hemis_pii_filtering_strictly_protects_privacy():
    """Shaxsga doir maxfiy ma'lumotlar (pasport, tug'ilgan sana, manzil) filtrlanishini tekshirish."""
    # Foydalanuvchi taqdim etgan to'liq real HEMIS javobi
    raw_hemis_payload = {
        "id": 7828,
        "first_name": "ZOXIDJON",
        "second_name": "QODIROV",
        "third_name": "TOHIR O‘G‘LI",
        "full_name": "QODIROV ZOXIDJON TOHIR O‘G‘LI",
        "short_name": "QODIROV Z. T.",
        "student_id_number": "401251200032",
        "passport_pin": "51806045390010",
        "image": "https://hemis.jbnuu.uz/static/crop/1/0/320_320_90_1026103993.jpg",
        "birth_date": 1087516800,
        "email": "zokhidjonyuta@gmail.com",
        "phone": "+998772501326",
        "gender": {"code": "11", "name": "Erkak"},
        "university": "Mirzo Ulug‘bek nomidagi O‘zbekiston Milliy universiteti Jizzax filiali",
        "specialty": {"id": "207ab7dc", "code": "70610401", "name": "Dasturiy injiniring"},
        "studentStatus": {"code": "11", "name": "O‘qimoqda"},
        "educationForm": {"code": "11", "name": "Kunduzgi"},
        "educationType": {"code": "12", "name": "Magistr"},
        "paymentForm": {"code": "11", "name": "Davlat granti"},
        "group": {"id": 422, "name": "M07-25"},
        "faculty": {"id": 42, "name": "MAGISTRATURA", "code": "401-103"},
        "level": {"code": "12", "name": "2-kurs"},
        "address": "Djizakskaya oblast, Djizakskiy rayon, Tokchilik ShFY, ul. Tokchilik, dom 24",
        "province": {"code": "1708", "name": "Jizzax viloyati"},
        "district": {"code": "1708212", "name": "Sharof Rashidov tumani"},
        "socialCategory": {"code": "10", "name": "Boshqa"},
        "povertyLevel": {"code": "10", "name": "Mavjud emas"},
        "accommodation": {"code": "11", "name": "O‘z uyida"},
        "validateUrl": "https://student.jbnuu.uz/api/info/student?h=08f55d6a",
        "hash": "fcd29e25368dcde2c9cee9b9c32dc46d42df0d121d180ba114562d6d8dbee95b"
    }

    filtered = HemisClient.filter_safe_academic_profile(raw_hemis_payload)

    # 1. Zarur akademik maydonlar to'g'ri olingan bo'lishi shart
    assert filtered["hemis_student_id"] == "401251200032"
    assert filtered["full_name"] == "QODIROV ZOXIDJON TOHIR O‘G‘LI"
    assert filtered["faculty"] == "MAGISTRATURA"
    assert filtered["group_name"] == "M07-25"
    assert filtered["course"] == 2
    assert filtered["specialty"] == "Dasturiy injiniring"
    assert filtered["education_type"] == "Magistr"
    assert filtered["education_form"] == "Kunduzgi"
    assert filtered["email"] == "zokhidjonyuta@gmail.com"
    assert filtered["phone"] == "+998772501326"

    # 2. SHAXSGA DOIR MA'LUMOTLAR QAT'IY YO'Q QILINISHI SHART!
    assert "passport_pin" not in filtered
    assert "birth_date" not in filtered
    assert "address" not in filtered
    assert "province" not in filtered
    assert "district" not in filtered
    assert "socialCategory" not in filtered
    assert "povertyLevel" not in filtered
    assert "accommodation" not in filtered
    assert "hash" not in filtered
    assert "validateUrl" not in filtered


async def test_student_hemis_login_and_profile(client: AsyncClient, test_db: AsyncSession):
    """HEMIS talaba login va 2 kunlik sessiya tekshiruvi."""
    # Seed a test student in test_db
    student = User(
        username="401251200032",
        hemis_student_id="401251200032",
        hashed_password=hash_password("(Zetmax0011)"),
        full_name="QODIROV ZOXIDJON TOHIR O‘G‘LI",
        role=UserRole.STUDENT,
        faculty="MAGISTRATURA",
        group_name="M07-25",
        course=2,
        specialty="Dasturiy injiniring",
        education_type="Magistr",
        education_form="Kunduzgi",
        email="zokhidjonyuta@gmail.com",
        phone="+998772501326"
    )
    test_db.add(student)
    await test_db.commit()

    # 1. Talaba tizimga login qiladi
    login_resp = await client.post(
        "/api/v1/auth/hemis-login",
        json={"hemis_login": "401251200032", "password": "(Zetmax0011)"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["role"] == "student"
    assert login_data["full_name"] == "QODIROV ZOXIDJON TOHIR O‘G‘LI"
    assert login_data["expires_in_minutes"] == 2880  # 2 kun (48 soat)
    access_token = login_data["access_token"]

    # 2. Profilini tekshirish (/auth/me)
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["hemis_student_id"] == "401251200032"
    assert me_data["specialty"] == "Dasturiy injiniring"
    assert me_data["faculty"] == "MAGISTRATURA"
    assert me_data["course"] == 2
    # Ensure no PII in response
    assert "passport_pin" not in me_data
    assert "address" not in me_data
