import logging
from fastapi import APIRouter, Request, HTTPException, Depends, status
import httpx
from app.core.config import settings
from app.services.telegram_bot import handle_telegram_update
from app.api.deps import require_role
from app.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram Bot Webhook"])


@router.post("/webhook", summary="Telegram botdan keluvchi yangilanishlarni qabul qilish (Webhook)")
async def telegram_webhook(request: Request):
    """
    Telegram Bot API tomonidan yuboriladigan update (xabar, kontakt, buyruq)larni qabul qiladi
    va avtomatik qayta ishlaydi.
    """
    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Noto'g'ri JSON formati")

    # Update'ni asinxron qayta ishlash
    try:
        await handle_telegram_update(update)
    except Exception as e:
        logger.error(f"Telegram webhook update'ni qayta ishlashda xatolik: {e}")

    return {"ok": True}


@router.post("/set-webhook", summary="Telegram botga webhook URL manzilini sozlash (faqat Admin)")
async def set_telegram_webhook(
    webhook_url: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Telegram botga rasmiy webhook manzilini o'rnatish."""
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN sozlanmagan.")

    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(api_url, json={"url": webhook_url})
        return resp.json()


@router.get("/webhook-info", summary="Telegram bot webhook holatini tekshirish (faqat Admin)")
async def get_telegram_webhook_info(
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Telegram botning hozirgi webhook holatini ko'rish."""
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN sozlanmagan.")

    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(api_url)
        return resp.json()
