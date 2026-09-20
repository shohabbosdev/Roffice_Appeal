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
    async def send_telegram_document(
        cls,
        chat_id: int,
        file_path: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> bool:
        """Telegram Bot API orqali fayl/hujjat jo'natish."""
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"

        try:
            import os
            if not os.path.exists(file_path):
                logger.error(f"Telegramga yuboriladigan fayl topilmadi: {file_path}")
                return False

            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()

            files = {"document": (filename, file_content)}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = parse_mode

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, data=data, files=files)
                if resp.status_code == 200:
                    logger.info(f"Telegram hujjat muvaffaqiyatli jo'natildi -> chat_id: {chat_id}")
                    return True
                else:
                    logger.warning(f"Telegram sendDocument xatosi ({resp.status_code}): {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Telegram sendDocument so'rovida xatolik: {e}")
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

    @classmethod
    async def notify_clarification_requested(
        cls, student_chat_id: Optional[int], appeal_ticket: str, clarification_message: str, service_title: str
    ):
        """Xodim qo'shimcha ma'lumot so'raganda talabaga xabar berish."""
        if not student_chat_id:
            return
        msg = (
            f"❓ <b>Murojaatingiz bo'yicha qo'shimcha ma'lumot so'raldi</b>\n\n"
            f"Sizning <b>#{appeal_ticket}</b> raqamli murojaatingiz ({service_title}) bo'yicha mas'ul xodim quyidagi ma'lumotlarni aniqlashtirishingizni so'ramoqda:\n\n"
            f"<b>Xodim xabari:</b>\n{clarification_message}\n\n"
            f"<i>Iltimos, Registrator ofisi portalidagi shaxsiy kabinetingizga kirib, so'ralgan ma'lumotni kiritishingiz so'raladi. "
            f"Siz javob bergunga qadar ijro taymeri vaqtincha to'xtatiladi.</i>"
        )
        await cls.send_telegram_message(student_chat_id, msg)

    @classmethod
    async def notify_clarification_provided(
        cls, staff_chat_id: Optional[int], appeal_ticket: str, student_name: str, clarification_response: str
    ):
        """Talaba tushuntirish kiritganda ijrochi xodimga xabar berish."""
        if not staff_chat_id:
            return
        msg = (
            f"💬 <b>Talaba so'ralgan ma'lumotni kiritdi</b>\n\n"
            f"• <b>Talon raqami:</b> #{appeal_ticket}\n"
            f"• <b>Talaba:</b> {student_name}\n\n"
            f"<b>Talabaning javobi:</b>\n{clarification_response}\n\n"
            f"<i>Murojaat bo'yicha ijro taymeri qayta tiklandi. Ko'rib chiqishingizni so'raymiz.</i>"
        )
        await cls.send_telegram_message(staff_chat_id, msg)

    @classmethod
    async def notify_appeal_disputed(
        cls, head_chat_id: Optional[int], appeal_ticket: str, student_name: str, dispute_reason: str
    ):
        """Talaba e'tiroz (nizo) ochganda Ofis boshlig'iga xabar berish."""
        if not head_chat_id:
            return
        msg = (
            f"⚖️ <b>Yangi nizoli murojaat (E'tiroz bildirildi)</b>\n\n"
            f"Talaba berilgan javobdan qanoatlanmadi va nizo ochdi:\n"
            f"• <b>Talon raqami:</b> #{appeal_ticket}\n"
            f"• <b>Talaba:</b> {student_name}\n\n"
            f"<b>E'tiroz sababi:</b>\n{dispute_reason}\n\n"
            f"<i>Murojaat 2-bosqich eskalatsiyasiga o'tkazildi. Ofis rahbariyati tomonidan hal etilishi lozim.</i>"
        )
        await cls.send_telegram_message(head_chat_id, msg)

    @classmethod
    async def notify_appeal_escalated_prorektor(
        cls, prorektor_chat_id: Optional[int], appeal_ticket: str, student_name: str, head_note: str
    ):
        """Ofis boshlig'i nizoni Prorektorga oshirganda xabar berish."""
        if not prorektor_chat_id:
            return
        msg = (
            f"🏛️ <b>Murojaat Prorektor nazoratiga oshirildi</b>\n\n"
            f"Registrator ofisi boshlig'i tomonidan nizoli murojaat Prorektorga yo'naltirildi:\n"
            f"• <b>Talon raqami:</b> #{appeal_ticket}\n"
            f"• <b>Talaba:</b> {student_name}\n\n"
            f"<b>Ofis boshlig'i xulosasi:</b>\n{head_note}\n\n"
            f"<i>Mazkur murojaat bo'yicha yakuniy qaror chiqarishingiz so'raladi.</i>"
        )
        await cls.send_telegram_message(prorektor_chat_id, msg)

    @classmethod
    async def notify_prorektor_decision(
        cls, chat_id: Optional[int], appeal_ticket: str, final_decision: str, is_student: bool = True
    ):
        """Prorektorning yakuniy qarori chiqqanda xabar berish."""
        if not chat_id:
            return
        role_label = "Hurmatli talaba," if is_student else "Hurmatli ijrochi xodim,"
        msg = (
            f"⚖️ <b>Prorektorning yakuniy qarori</b>\n\n"
            f"{role_label}\n"
            f"<b>#{appeal_ticket}</b> raqamli murojaat bo'yicha O'quv ishlari bo'yicha prorektorning yakuniy rasmiy qarori qabul qilindi:\n\n"
            f"<b>Qaror matni:</b>\n{final_decision}\n\n"
            f"<i>Ushbu qaror qat'iy va majburiy hisoblanadi. Murojaat to'liq yopildi.</i>"
        )
        await cls.send_telegram_message(chat_id, msg)

    @classmethod
    async def notify_appointment_called(
        cls, student_chat_id: Optional[int], ticket_code: str, window_number: str
    ):
        """Front-ofis xodimi talabani darchaga chaqirganda bildirishnoma."""
        if not student_chat_id:
            return
        msg = (
            f"📢 <b>Sizning navbatingiz keldi!</b>\n\n"
            f"Hurmatli talaba, sizning <code>{ticket_code}</code> raqamli taloningiz darchaga chaqirilmoqda:\n\n"
            f"🏛️ <b>Qabul joyi:</b> {window_number}\n\n"
            f"<i>Iltimos, zudlik bilan ko'rsatilgan darchaga yetib boring!</i>"
        )
        await cls.send_telegram_message(student_chat_id, msg)

    @classmethod
    async def notify_appointment_reminder(
        cls, student_chat_id: Optional[int], ticket_code: str, window_number: str, time_slot: str, service_title: str
    ):
        """Darcha qabuliga 30 daqiqa qolganda avtomatik eslatma."""
        if not student_chat_id:
            return
        msg = (
            f"⏰ <b>Qabul navbatingizga 30 daqiqa qoldi!</b>\n\n"
            f"Hurmatli talaba, bugungi darcha qabulingiz vaqti yaqinlashmoqda:\n"
            f"• <b>Talon:</b> <code>{ticket_code}</code>\n"
            f"• <b>Xizmat:</b> {service_title}\n"
            f"• <b>Darcha:</b> {window_number}\n"
            f"• <b>Vaqti:</b> {time_slot}\n\n"
            f"<i>Iltimos, belgilangan vaqtda Registrator ofisiga (104-xona) shaxsingizni tasdiqlovchi hujjat bilan yetib keling.</i>"
        )
        await cls.send_telegram_message(student_chat_id, msg)

