import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import User, Appeal, Service, Appointment
from app.services.telegram_service import TelegramService
from app.services.telegram_bot import handle_telegram_update


@pytest.mark.asyncio
async def test_telegram_info_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as front staff
        login_resp = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get telegram info
        info_resp = await ac.get("/api/v1/auth/telegram-info", headers=headers)
        assert info_resp.status_code == 200
        data = info_resp.json()
        assert "bot_username" in data
        assert "deep_link" in data
        assert "is_connected" in data
        assert "t.me" in data["deep_link"]


@pytest.mark.asyncio
async def test_telegram_deep_link_binding():
    unique_suffix = uuid.uuid4().hex[:6]
    unique_chat_id = uuid.uuid4().int % 1000000000
    test_user_id = None

    # Create a user to test binding
    async with AsyncSessionLocal() as db:
        user = User(
            username=f"tg_user_{unique_suffix}",
            hashed_password="hashed_pass_sample",
            full_name="Telegram Test User",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        test_user_id = user.id

    # Simulate deep-link /start bind_<user_id>
    update = {
        "update_id": 1001,
        "message": {
            "message_id": 1,
            "from": {"id": unique_chat_id, "username": f"user_{unique_suffix}"},
            "chat": {"id": unique_chat_id},
            "text": f"/start bind_{test_user_id}"
        }
    }

    await handle_telegram_update(update)

    # Check user in DB
    async with AsyncSessionLocal() as db:
        updated_user = await db.get(User, test_user_id)
        assert updated_user.telegram_chat_id == unique_chat_id
        assert updated_user.telegram_username == f"user_{unique_suffix}"
        assert updated_user.telegram_connected_at is not None


@pytest.mark.asyncio
async def test_telegram_contact_validation_and_binding(monkeypatch):
    unique_suffix = uuid.uuid4().hex[:6]
    unique_digits = f"{uuid.uuid4().int % 10000000:07d}"
    test_phone = f"+99893{unique_digits}"
    student_id = f"4012{unique_suffix}"

    # Create student in DB
    async with AsyncSessionLocal() as db:
        user = User(
            username=student_id,
            hashed_password="hashed_pass_sample",
            full_name="Valid Phone Student",
            hemis_student_id=student_id,
            phone=test_phone,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Mock TelegramService.validate_phone_with_jbnuu to return simulated university response
    async def mock_validate_success(phone):
        return {
            "success": True,
            "error": None,
            "data": {
                "type": "student",
                "id": 99,
                "employee_id_number": student_id
            },
            "code": 200
        }

    monkeypatch.setattr(TelegramService, "validate_phone_with_jbnuu", mock_validate_success)

    contact_chat_id = uuid.uuid4().int % 1000000000

    # Simulate contact message from Telegram
    update = {
        "update_id": 1002,
        "message": {
            "message_id": 2,
            "from": {"id": contact_chat_id, "username": f"tg_student_{unique_suffix}"},
            "chat": {"id": contact_chat_id},
            "contact": {
                "phone_number": test_phone,
                "first_name": "Valid"
            }
        }
    }

    await handle_telegram_update(update)

    # Verify user was matched and linked
    async with AsyncSessionLocal() as db:
        updated_user = (await db.execute(
            User.__table__.select().where(User.hemis_student_id == student_id)
        )).first()
        assert updated_user.telegram_chat_id == contact_chat_id
        assert updated_user.telegram_username == f"tg_student_{unique_suffix}"


@pytest.mark.asyncio
async def test_telegram_contact_validation_failure(monkeypatch):
    # Mock TelegramService.validate_phone_with_jbnuu to return 404
    async def mock_validate_fail(phone):
        return {
            "success": False,
            "error": "+998931189981 not found",
            "data": [],
            "code": 404
        }

    monkeypatch.setattr(TelegramService, "validate_phone_with_jbnuu", mock_validate_fail)

    update = {
        "update_id": 1003,
        "message": {
            "message_id": 3,
            "from": {"id": 77665544, "username": "unknown_phone"},
            "chat": {"id": 77665544},
            "contact": {
                "phone_number": "+998931189981",
                "first_name": "Unknown"
            }
        }
    }

    # Should not raise exception
    await handle_telegram_update(update)
