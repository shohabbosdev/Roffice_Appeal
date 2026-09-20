import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import SystemSetting, User
from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret, mask_secret
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

KEY_TG_BOT_TOKEN = "telegram_bot_token"
KEY_TG_BOT_USERNAME = "telegram_bot_username"
KEY_ADMIN_TG_ID = "admin_telegram_id"
KEY_JBNUU_API_TOKEN = "jbnuu_api_token"


class IntegrationService:
    """Telegram Bot va HEMIS integratsiya sozlamalarini xavfsiz boshqarish."""

    @staticmethod
    async def get_raw_setting(db: AsyncSession, key: str) -> Optional[str]:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        setting = (await db.execute(stmt)).scalar_one_or_none()
        return setting.value if setting else None

    @staticmethod
    async def set_raw_setting(db: AsyncSession, key: str, value: str) -> None:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        setting = (await db.execute(stmt)).scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)

    @classmethod
    async def get_integration_settings(cls, db: AsyncSession, for_admin_ui: bool = True) -> Dict[str, Any]:
        """
        Bazada saqlangan integratsiya parametrlarini olish.
        Agar bazada bo'lmasa, settings dan olinadi.
        """
        # 1. Telegram Bot Token
        raw_tg_token = await cls.get_raw_setting(db, KEY_TG_BOT_TOKEN)
        if raw_tg_token:
            tg_token = decrypt_secret(raw_tg_token)
        else:
            tg_token = settings.TELEGRAM_BOT_TOKEN or ""

        # 2. Telegram Bot Username
        raw_tg_user = await cls.get_raw_setting(db, KEY_TG_BOT_USERNAME)
        tg_username = raw_tg_user if raw_tg_user else (settings.TELEGRAM_BOT_USERNAME or "")

        # 3. Admin Telegram ID
        raw_admin_id = await cls.get_raw_setting(db, KEY_ADMIN_TG_ID)
        try:
            admin_tg_id = int(raw_admin_id) if raw_admin_id else settings.ADMIN_TELEGRAM_ID
        except (ValueError, TypeError):
            admin_tg_id = settings.ADMIN_TELEGRAM_ID

        # 4. JBNUU HEMIS API Token
        raw_jbnuu_token = await cls.get_raw_setting(db, KEY_JBNUU_API_TOKEN)
        if raw_jbnuu_token:
            jbnuu_token = decrypt_secret(raw_jbnuu_token)
        else:
            jbnuu_token = settings.JBNUU_API_TOKEN or ""

        if for_admin_ui:
            return {
                "telegram_bot_username": tg_username.lstrip("@"),
                "telegram_bot_token_masked": mask_secret(tg_token),
                "is_telegram_bot_configured": bool(tg_token),
                "admin_telegram_id": admin_tg_id,
                "jbnuu_api_token_masked": mask_secret(jbnuu_token),
                "is_jbnuu_token_configured": bool(jbnuu_token)
            }

        return {
            "telegram_bot_token": tg_token,
            "telegram_bot_username": tg_username.lstrip("@"),
            "admin_telegram_id": admin_tg_id,
            "jbnuu_api_token": jbnuu_token
        }

    @classmethod
    async def update_integration_settings(
        cls,
        db: AsyncSession,
        data: Dict[str, Any],
        admin_user: User,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Integratsiya sozlamalarini yangilash.
        Maxfiy tokenlar shifrlab saqlanadi, settings obyekti sinxron yangilanadi.
        """
        changes = {}

        # 1. Telegram Bot Token
        if "telegram_bot_token" in data and data["telegram_bot_token"] is not None:
            new_val = str(data["telegram_bot_token"]).strip()
            if new_val:
                enc = encrypt_secret(new_val)
                await cls.set_raw_setting(db, KEY_TG_BOT_TOKEN, enc)
                settings.TELEGRAM_BOT_TOKEN = new_val
                changes["telegram_bot_token"] = "Yangi token shifrlab saqlandi"

        # 2. Telegram Bot Username
        if "telegram_bot_username" in data and data["telegram_bot_username"] is not None:
            new_user = str(data["telegram_bot_username"]).strip().lstrip("@")
            if new_user:
                await cls.set_raw_setting(db, KEY_TG_BOT_USERNAME, new_user)
                settings.TELEGRAM_BOT_USERNAME = new_user
                changes["telegram_bot_username"] = new_user

        # 3. Admin Telegram ID
        if "admin_telegram_id" in data and data["admin_telegram_id"] is not None:
            try:
                new_id = int(data["admin_telegram_id"])
                await cls.set_raw_setting(db, KEY_ADMIN_TG_ID, str(new_id))
                settings.ADMIN_TELEGRAM_ID = new_id
                changes["admin_telegram_id"] = new_id
            except (ValueError, TypeError):
                pass

        # 4. JBNUU HEMIS API Token
        if "jbnuu_api_token" in data and data["jbnuu_api_token"] is not None:
            new_val = str(data["jbnuu_api_token"]).strip()
            if new_val:
                enc = encrypt_secret(new_val)
                await cls.set_raw_setting(db, KEY_JBNUU_API_TOKEN, enc)
                settings.JBNUU_API_TOKEN = new_val
                changes["jbnuu_api_token"] = "Yangi HEMIS token shifrlab saqlandi"

        await db.commit()

        # Audit log
        await AuditService.log(
            db=db,
            user_id=admin_user.id,
            action="UPDATE_INTEGRATION_SETTINGS",
            entity_type="SYSTEM_SETTINGS",
            entity_id=0,
            ip_address=ip_address,
            changes=changes
        )

        return await cls.get_integration_settings(db, for_admin_ui=True)

    @classmethod
    async def init_defaults(cls, db: AsyncSession) -> None:
        """
        Boshlang'ich qiymatlarni o'rnatish:
        Bot: @rofficejbnuubot
        Token: 8571976188:AAFwPnt_HjeXyDTZH-UWo2iaPC7s9kuL3Yk
        Admin ID: 8515413686
        """
        default_tg_token = "8571976188:AAFwPnt_HjeXyDTZH-UWo2iaPC7s9kuL3Yk"
        default_tg_user = "rofficejbnuubot"
        default_admin_id = "8515413686"

        existing_token = await cls.get_raw_setting(db, KEY_TG_BOT_TOKEN)
        if not existing_token:
            await cls.set_raw_setting(db, KEY_TG_BOT_TOKEN, encrypt_secret(default_tg_token))
            settings.TELEGRAM_BOT_TOKEN = default_tg_token

        existing_user = await cls.get_raw_setting(db, KEY_TG_BOT_USERNAME)
        if not existing_user:
            await cls.set_raw_setting(db, KEY_TG_BOT_USERNAME, default_tg_user)
            settings.TELEGRAM_BOT_USERNAME = default_tg_user

        existing_admin_id = await cls.get_raw_setting(db, KEY_ADMIN_TG_ID)
        if not existing_admin_id:
            await cls.set_raw_setting(db, KEY_ADMIN_TG_ID, default_admin_id)
            settings.ADMIN_TELEGRAM_ID = int(default_admin_id)

        await db.commit()
