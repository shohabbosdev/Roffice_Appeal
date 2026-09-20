import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import decrypt_secret
from app.services.integration_service import IntegrationService, KEY_TG_BOT_TOKEN, KEY_JBNUU_API_TOKEN


@pytest.mark.asyncio
async def test_integration_settings_rbac_and_encryption():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        admin_res = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123!"
        })
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Front staff login (Malika)
        staff_res = await ac.post("/api/v1/auth/login", json={
            "username": "malika_front",
            "password": "StaffPass123!"
        })
        assert staff_res.status_code == 200
        staff_token = staff_res.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # 3. Office Head login (Akrom)
        head_res = await ac.post("/api/v1/auth/login", json={
            "username": "akrom_head",
            "password": "HeadPass123!"
        })
        assert head_res.status_code == 200
        head_token = head_res.json()["access_token"]
        head_headers = {"Authorization": f"Bearer {head_token}"}

        # -------------------------------------------------------------
        # RBAC CHEKLOV: Boshqa rollar uchun GET va PUT 403 qaytarishi shart!
        # -------------------------------------------------------------
        staff_get = await ac.get("/api/v1/system/integrations", headers=staff_headers)
        assert staff_get.status_code == 403

        head_get = await ac.get("/api/v1/system/integrations", headers=head_headers)
        assert head_get.status_code == 403

        staff_put = await ac.put("/api/v1/system/integrations", headers=staff_headers, json={
            "telegram_bot_username": "hacked_bot"
        })
        assert staff_put.status_code == 403

        head_put = await ac.put("/api/v1/system/integrations", headers=head_headers, json={
            "telegram_bot_username": "hacked_bot"
        })
        assert head_put.status_code == 403

        # -------------------------------------------------------------
        # ADMIN: GET va PUT to'liq ruxsat etilgan
        # -------------------------------------------------------------
        admin_get = await ac.get("/api/v1/system/integrations", headers=admin_headers)
        assert admin_get.status_code == 200
        data = admin_get.json()
        assert "telegram_bot_username" in data
        assert "admin_telegram_id" in data
        assert "telegram_bot_token_masked" in data
        assert "jbnuu_api_token_masked" in data

        # Yangi maxfiy tokenlar bilan yangilash
        test_bot_token = "8571976188:AAFwPnt_HjeXyDTZH-UWo2iaPC7s9kuL3Yk"
        test_hemis_token = f"hemis_super_secret_token_{uuid.uuid4().hex}"
        test_admin_id = 8515413686

        admin_put = await ac.put("/api/v1/system/integrations", headers=admin_headers, json={
            "telegram_bot_username": "rofficejbnuubot",
            "telegram_bot_token": test_bot_token,
            "admin_telegram_id": test_admin_id,
            "jbnuu_api_token": test_hemis_token
        })
        assert admin_put.status_code == 200
        put_data = admin_put.json()
        assert put_data["telegram_bot_username"] == "rofficejbnuubot"
        assert put_data["admin_telegram_id"] == test_admin_id
        assert put_data["is_telegram_bot_configured"] is True
        assert put_data["is_jbnuu_token_configured"] is True

        # Bazadagi qiymatlarni tekshirish: SHIFRLANGAN holda saqlanganligini tasdiqlash
        async with AsyncSessionLocal() as db:
            raw_bot_token = await IntegrationService.get_raw_setting(db, KEY_TG_BOT_TOKEN)
            raw_hemis_token = await IntegrationService.get_raw_setting(db, KEY_JBNUU_API_TOKEN)

            # Bazadagi xom qiymat ochiq matn EMAS, shifrlangan bo'lishi kerak!
            assert raw_bot_token.startswith("enc$v1$")
            assert raw_hemis_token.startswith("enc$v1$")
            assert test_bot_token not in raw_bot_token
            assert test_hemis_token not in raw_hemis_token

            # Lekin decrypt qilinganda aynan kiritilgan qiymat qaytishi kerak
            assert decrypt_secret(raw_bot_token) == test_bot_token
            assert decrypt_secret(raw_hemis_token) == test_hemis_token
