import logging
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram Bot va JBNUU HEMIS telefon validatsiyasi xizmati."""

    @staticmethod
    def format_phone_number(phone: str) -> str:
        """Telefon raqamni toza +998XXXXXXXXX formatga keltiradi."""
        clean = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if not clean.startswith("+"):
            clean = "+" + clean
        return clean

    @classmethod
    async def validate_phone_with_jbnuu(cls, phone: str) -> Dict[str, Any]:
        """
        Universitet HEMIS tizimi orqali telefon raqamini tekshirish:
        GET https://student.jbnuu.uz/rest/v1/data/validate-phone?phone=%2B998931189988
        Header: Authorization: Bearer {JBNUU_API_TOKEN}
        """
        formatted = cls.format_phone_number(phone)
        url = f"{settings.JBNUU_VALIDATE_PHONE_URL}?phone={urllib.parse.quote(formatted)}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.JBNUU_API_TOKEN}"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                data = resp.json()
                logger.info(f"JBNUU Validate-phone javobi ({formatted}): {data}")
                return data
        except Exception as e:
            logger.error(f"JBNUU Validate-phone API so'rovida xatolik: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "code": 500
            }

    @classmethod
    async def send_telegram_message(
        cls,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML"
    ) -> bool:
        """Telegram Bot API orqali xabar jo'natish."""
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.debug("Telegram bot tokeni ko'rsatilmagan, xabar jo'natilmadi.")
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return True
                else:
                    logger.warning(f"Telegramga xabar yuborishda xatolik: {resp.status_code} - {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Telegram API ulanish xatosi: {e}")
            return False

    @classmethod
    async def notify_appeal_created(cls, chat_id: Optional[int], appeal_ticket: str, subject: str, service_title: str, deadline: Optional[datetime] = None):
        """Yangi murojaat yaratilganda talabaga xabar yuborish."""
        if not chat_id:
            return
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M") if deadline else "Reglament asosida"
        msg = (
            f"📌 <b>Murojaatingiz qabul qilindi</b>\n\n"
            f"Hurmatli talaba, sizning murojaatingiz muvaffaqiyatli ro'yxatga olindi:\n"
            f"• <b>Talon raqami:</b> #{appeal_ticket}\n"
            f"• <b>Mavzu:</b> {subject}\n"
            f"• <b>Xizmat:</b> {service_title}\n"
            f"• <b>SLA ijro muddati:</b> {deadline_str}\n\n"
            f"<i>Ijrochi biriktirilganda va rasmiy javob berilganda sizga xabar yetkaziladi.</i>"
        )
        await cls.send_telegram_message(chat_id, msg)

    @classmethod
    async def notify_appeal_assigned(cls, staff_chat_id: Optional[int], appeal_ticket: str, subject: str, student_name: str, deadline: Optional[datetime] = None):
        """Xodimga yangi murojaat biriktirilganda ogohlantirish."""
        if not staff_chat_id:
            return
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M") if deadline else "Reglament asosida"
        msg = (
            f"🔔 <b>Sizga yangi murojaat biriktirildi</b>\n\n"
            f"• <b>Talon raqami:</b> #{appeal_ticket}\n"
            f"• <b>Mavzu:</b> {subject}\n"
            f"• <b>Talaba:</b> {student_name}\n"
            f"• <b>Ijro muddati (SLA):</b> {deadline_str}\n\n"
            f"<i>Murojaatni o'z vaqtida ko'rib chiqib, ijro etishingiz so'raladi.</i>"
        )
        await cls.send_telegram_message(staff_chat_id, msg)

    @classmethod
    async def notify_appeal_resolved(cls, student_chat_id: Optional[int], appeal_ticket: str, subject: str, resolution_text: str):
        """Murojaatga javob berilganda talabaga xabar yuborish."""
        if not student_chat_id:
            return
        msg = (
            f"✅ <b>Murojaatingiz ko'rib chiqildi va yakunlandi</b>\n\n"
            f"Sizning <b>#{appeal_ticket}</b> ({subject}) murojaatingizga rasmiy ijro javobi berildi:\n\n"
            f"<b>Ijro javobi:</b>\n{resolution_text}\n\n"
            f"<i>Shaxsiy kabinetingiz orqali ijro sifatini 1 dan 5 gacha baholashingiz mumkin.</i>"
        )
        await cls.send_telegram_message(student_chat_id, msg)

    @classmethod
    async def notify_appointment_booked(cls, student_chat_id: Optional[int], ticket_code: str, window_number: str, appointment_date: str, time_slot: str, service_title: str):
        """Darcha qabuliga navbat olinganda talabaga talon xabarnomasi."""
        if not student_chat_id:
            return
        msg = (
            f"🎫 <b>Darcha qabuliga elektron navbat taloni olindi</b>\n\n"
            f"• <b>Talon kodi:</b> <code>{ticket_code}</code>\n"
            f"• <b>Xizmat:</b> {service_title}\n"
            f"• <b>Darcha:</b> {window_number}\n"
            f"• <b>Qabul sanasi:</b> {appointment_date}\n"
            f"• <b>Vaqt oralig'i:</b> {time_slot}\n\n"
            f"<i>Iltimos, ko'rsatilgan vaqtda 104-xonaga ({window_number}) shaxsingizni tasdiqlovchi hujjat bilan tashrif buyuring.</i>"
        )
        await cls.send_telegram_message(student_chat_id, msg)
