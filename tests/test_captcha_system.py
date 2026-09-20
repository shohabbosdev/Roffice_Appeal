import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.config import settings
from app.models import CaptchaChallenge
from app.services.captcha_service import CaptchaService


@pytest.mark.asyncio
async def test_captcha_generate_endpoint(client: AsyncClient):
    """GET /api/v1/auth/captcha orqali yangi bir martalik SVG Captcha olishni tekshirish."""
    resp = await client.get("/api/v1/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    assert "captcha_id" in data
    assert "captcha_svg" in data
    assert len(data["captcha_id"]) >= 30
    assert "<svg" in data["captcha_svg"]
    assert "</svg>" in data["captcha_svg"]


@pytest.mark.asyncio
async def test_captcha_verification_success_and_case_insensitivity(test_db: AsyncSession):
    """To'g'ri kod bilan tekshiruv va kichik harflarga avtomatik konvertatsiya bo'lishini tekshirish."""
    # Qo'lda sinov kodi bilan challenge yaratamiz
    code = "ab2c"
    challenge_id = "test-uuid-challenge-1"
    now = datetime.now(timezone.utc)
    hashed = CaptchaService._hash_code(code)

    challenge = CaptchaChallenge(
        id=challenge_id,
        hashed_code=hashed,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        is_used=False
    )
    test_db.add(challenge)
    await test_db.commit()

    # Katta harflar bilan kiritilsa ham kichik harflarda qabul qilinishi kerak
    res = await CaptchaService.verify_challenge(
        db=test_db,
        captcha_id=challenge_id,
        user_code="AB2C"
    )
    assert res is True

    # Tekshirilgach darhol bazadan o'chirilishi kerak (bir martalik kafolat)
    deleted = await test_db.get(CaptchaChallenge, challenge_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_captcha_replay_attack_prevention(test_db: AsyncSession):
    """Bir marta ishlatilgan captchani ikkinchi marta ishlatish (replay attack) qat'iy taqiqlanishi."""
    code = "xy8z"
    challenge_id = "test-uuid-challenge-2"
    now = datetime.now(timezone.utc)
    hashed = CaptchaService._hash_code(code)

    challenge = CaptchaChallenge(
        id=challenge_id,
        hashed_code=hashed,
        created_at=now,
        expires_at=now + timedelta(seconds=120),
        is_used=False
    )
    test_db.add(challenge)
    await test_db.commit()

    # 1-marta to'g'ri tekshiriladi
    await CaptchaService.verify_challenge(test_db, challenge_id, "xy8z")

    # 2-marta aynan o'sha captcha_id bilan urinilganda 400 xatolik berishi shart!
    with pytest.raises(HTTPException) as exc_info:
        await CaptchaService.verify_challenge(test_db, challenge_id, "xy8z")
    assert exc_info.value.status_code == 400
    assert "topilmadi" in exc_info.value.detail or "allaqachon ishlatilgan" in exc_info.value.detail


@pytest.mark.asyncio
async def test_captcha_expired(test_db: AsyncSession):
    """Muddati (2 daqiqa) o'tgan captchaning rad etilishi."""
    code = "expired1"
    challenge_id = "test-uuid-challenge-expired"
    now = datetime.now(timezone.utc)
    hashed = CaptchaService._hash_code(code)

    challenge = CaptchaChallenge(
        id=challenge_id,
        hashed_code=hashed,
        created_at=now - timedelta(minutes=5),
        expires_at=now - timedelta(minutes=3),  # Muddati o'tib ketgan
        is_used=False
    )
    test_db.add(challenge)
    await test_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await CaptchaService.verify_challenge(test_db, challenge_id, code)
    assert exc_info.value.status_code == 400
    assert "muddati o'tgan" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_blocked_without_valid_captcha(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    """Ishlab chiqarish rejimida captchasiz yoki noto'g'ri captcha bilan kirishning to'liq bloklanishi."""
    staff = seed_test_data["staff"]

    orig_testing = settings.TESTING
    try:
        # Haqiqiy production rejimini simulyatsiya qilamiz
        settings.TESTING = False

        # 1. Captcha umuman kiritilmaganda bloklanadi
        resp_no_captcha = await client.post("/api/v1/auth/login", json={
            "username": staff.username,
            "password": "WrongOrRightPassword"
        })
        assert resp_no_captcha.status_code == 400
        assert "Captcha kodi kiritilishi shart" in resp_no_captcha.json()["detail"]

        # 2. Soxta / mavjud bo'lmagan captcha kiritilganda bloklanadi
        resp_bad_captcha = await client.post("/api/v1/auth/login", json={
            "username": staff.username,
            "password": "StaffPass123!",
            "captcha_id": "non-existent-captcha-id",
            "captcha_code": "abcd"
        })
        assert resp_bad_captcha.status_code == 400
        assert "Captcha topilmadi" in resp_bad_captcha.json()["detail"]

        # 3. Haqiqiy to'g'ri Captcha bilan muvaffaqiyatli kirish
        code = "pass7"
        challenge_id = "valid-captcha-for-login-test"
        now = datetime.now(timezone.utc)
        hashed = CaptchaService._hash_code(code)

        challenge = CaptchaChallenge(
            id=challenge_id,
            hashed_code=hashed,
            created_at=now,
            expires_at=now + timedelta(seconds=120),
            is_used=False
        )
        test_db.add(challenge)
        await test_db.commit()

        resp_ok = await client.post("/api/v1/auth/login", json={
            "username": staff.username,
            "password": "Pass123!",
            "captcha_id": challenge_id,
            "captcha_code": "PASS7"  # Katta harfda kiritilganda ham kichik harf deb o'tishi kerak
        })
        assert resp_ok.status_code == 200
        assert "access_token" in resp_ok.json()

    finally:
        settings.TESTING = orig_testing
