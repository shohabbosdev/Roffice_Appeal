import json
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import SystemSetting

DEFAULT_ALLOWED_EDUCATION_FORMS = ["sirtqi", "masofaviy", "kechki"]

ALL_EDUCATION_FORMS: List[Dict[str, str]] = [
    {
        "code": "kunduzgi",
        "title": "Kunduzgi ta'lim",
        "description": "Kunduzgi ta'lim talabalari (odatda 104-xonaga kelib hal etish tavsiya etiladi)"
    },
    {
        "code": "sirtqi",
        "title": "Sirtqi ta'lim",
        "description": "Sirtqi ta'lim shakli talabalari uchun masofaviy murojaat"
    },
    {
        "code": "masofaviy",
        "title": "Masofaviy ta'lim",
        "description": "Masofaviy ta'lim talabalari uchun to'liq onlayn ariza"
    },
    {
        "code": "kechki",
        "title": "Kechki ta'lim",
        "description": "Kechki ta'lim shakli talabalari uchun masofaviy qabul"
    }
]

SETTING_KEY = "allowed_education_forms"


class PolicyService:
    @staticmethod
    async def get_allowed_education_forms(db: AsyncSession) -> List[str]:
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == SETTING_KEY))
        setting = result.scalar_one_or_none()
        if not setting:
            return list(DEFAULT_ALLOWED_EDUCATION_FORMS)
        try:
            data = json.loads(setting.value)
            if isinstance(data, list):
                return [str(x).strip().lower() for x in data]
        except Exception:
            pass
        return list(DEFAULT_ALLOWED_EDUCATION_FORMS)

    @staticmethod
    async def get_education_form_policy(db: AsyncSession) -> Dict[str, Any]:
        allowed = await PolicyService.get_allowed_education_forms(db)
        items = []
        for form in ALL_EDUCATION_FORMS:
            code = form["code"]
            is_allowed = code in allowed
            items.append({
                "code": code,
                "title": form["title"],
                "allowed": is_allowed,
                "description": form["description"]
            })
        return {
            "allowed_forms": allowed,
            "items": items
        }

    @staticmethod
    async def update_education_form_policy(db: AsyncSession, allowed_forms: List[str]) -> Dict[str, Any]:
        clean_forms = [str(x).strip().lower() for x in allowed_forms if str(x).strip()]
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == SETTING_KEY))
        setting = result.scalar_one_or_none()
        if not setting:
            setting = SystemSetting(
                key=SETTING_KEY,
                value=json.dumps(clean_forms)
            )
            db.add(setting)
        else:
            setting.value = json.dumps(clean_forms)
        await db.commit()
        await db.refresh(setting)
        return await PolicyService.get_education_form_policy(db)
