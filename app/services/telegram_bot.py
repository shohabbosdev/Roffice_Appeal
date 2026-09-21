import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from sqlalchemy import select, or_
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import verify_telegram_bind_token
from app.models import User
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


async def handle_telegram_update(update: dict):
    """Bitta Telegram update (xabar)ni qayta ishlash."""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    user_info = message.get("from", {})
    username = user_info.get("username")
    text = message.get("text", "").strip() if message.get("text") else ""
    contact = message.get("contact")

    if not chat_id:
        return

    async with AsyncSessionLocal() as db:
        # 1. /start buyrug'i (yoki xavfsiz vaqtinchalik deep-link: /start bind_TOKEN)
        if text.startswith("/start"):
            if "bind_" in text:
                try:
                    token_str = text.split("bind_")[1].strip()
                    user_id = verify_telegram_bind_token(token_str)

                    # Agar token yaroqsiz, soxta yoki 15 daqiqadan oshgan bo'lsa
                    if not user_id:
                        err_link_msg = (
                            "❌ <b>Xavfsizlik ogohlantirishi:</b>\n\n"
                            "Ushbu bog'lanish havolasi eskirgan, yaroqsiz yoki noto'g'ri.\n\n"
                            "Iltimos, Registrator ofisi portalidagi shaxsiy kabinetingizga kirib, "
                            "yangilangan 'Telegram botga ulanish' tugmasi orqali qayta o'ting."
                        )
                        await TelegramService.send_telegram_message(chat_id, err_link_msg)
                        return

                    user = await db.get(User, user_id)
                    if user:
                        user.telegram_chat_id = chat_id
                        user.telegram_username = username
                        user.telegram_connected_at = datetime.now(timezone.utc)
                        await db.commit()

                        role_name = getattr(user.role, "value", str(user.role))
                        msg = (
                            f"Assalomu alaykum, <b>{user.full_name}</b>!\n\n"
                            f"Registrator ofisi axborot tizimidagi profilingiz botga muvaffaqiyatli bog'landi! ✅\n\n"
                            f"• <b>Foydalanuvchi logini:</b> {user.username}\n"
                            f"• <b>Rolingiz:</b> {role_name}\n"
                            f"• <b>Bog'langan vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                            f"Endi barcha arizalar, ijro holatlari va elektron navbat talonlari "
                            f"to'g'ridan-to'g'ri ushbu bot orqali yetkaziladi."
                        )
                        await TelegramService.send_telegram_message(
                            chat_id=chat_id,
                            text=msg,
                            reply_markup={"remove_keyboard": True}
                        )
                        return
                except Exception as e:
                    logger.error(f"Deep link orqali bog'lashda xatolik: {e}")

            # Oddiy /start: Agar allaqachon bog'langan bo'lsa
            stmt = select(User).where(User.telegram_chat_id == chat_id)
            existing_user = (await db.execute(stmt)).scalars().first()
            if existing_user:
                msg = (
                    f"Assalomu alaykum, <b>{existing_user.full_name}</b>!\n\n"
                    f"Sizning profilingiz allaqachon Registrator ofisi botiga ulangan. "
                    f"Barcha yangi bildirishnomalar shu yerga yetkaziladi."
                )
                await TelegramService.send_telegram_message(chat_id, msg)
                return

            # Agar ulanmagan bo'lsa -> "Telefon raqamni yuborish" tugmasini chiqarish
            keyboard = {
                "keyboard": [
                    [{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True
            }
            welcome_msg = (
                f"Assalomu alaykum!\n\n"
                f"Mirzo Ulug'bek nomidagi O'zMU Jizzax filiali <b>Registrator ofisi</b> "
                f"rasmiy bildirishnoma botiga xush kelibsiz.\n\n"
                f"Profilingizni avtomatik aniqlash va arizalaringiz bo'yicha tezkor xabarlarni "
                f"qabul qilish uchun iltimos, pastdagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing:"
            )
            await TelegramService.send_telegram_message(chat_id, welcome_msg, reply_markup=keyboard)
            return

        # 2. Foydalanuvchi kontakt (telefon raqam) yuborganida
        if contact:
            sender_id = user_info.get("id")
            contact_user_id = contact.get("user_id")

            # Xavfsizlik: Boshqa shaxsning kontakt kartasini forward qilib yuborishning oldini olish
            if contact_user_id and sender_id and contact_user_id != sender_id:
                warn_msg = (
                    "❌ <b>Xavfsizlik talabi:</b>\n\n"
                    "Siz boshqa shaxsning kontakt ma'lumotini yubordingiz. "
                    "Iltimos, faqat o'zingizning Telegram akkauntingizga biriktirilgan telefon raqamni "
                    "pastdagi <b>'📱 Telefon raqamni yuborish'</b> tugmasi orqali jo'nating."
                )
                await TelegramService.send_telegram_message(chat_id, warn_msg)
                return

            phone_raw = contact.get("phone_number", "")
            formatted_phone = TelegramService.format_phone_number(phone_raw)
            digits_only = "".join(ch for ch in phone_raw if ch.isdigit())
            last_9 = digits_only[-9:] if len(digits_only) >= 9 else digits_only

            # -----------------------------------------------------------------
            # 1-BOSQICH: Eng avvalo mahalliy bazamizdagi xodimlar va foydalanuvchilarni
            # kiritilgan telefon raqami bo'yicha to'g'ridan-to'g'ri tekshirish.
            # Bu HEMISga qaramlikni yo'qotadi va xodimlar uchun tezkor bog'lanishni ta'minlaydi.
            # -----------------------------------------------------------------
            local_conditions = [
                User.phone == formatted_phone,
                User.phone == digits_only,
            ]
            if len(digits_only) >= 9:
                local_conditions.append(User.phone.endswith(last_9))

            local_user = (await db.execute(
                select(User).where(or_(*local_conditions))
            )).scalars().first()

            if local_user:
                local_user.telegram_chat_id = chat_id
                local_user.telegram_username = username
                local_user.telegram_connected_at = datetime.now(timezone.utc)
                if not local_user.phone:
                    local_user.phone = formatted_phone
                await db.commit()

                local_role = getattr(local_user.role, "value", str(local_user.role))
                success_msg = (
                    f"🎉 <b>Hurmatli {local_user.full_name}!</b>\n\n"
                    f"Registrator ofisi axborot tizimidagi profilingiz telefon raqamingiz orqali "
                    f"muvaffaqiyatli tasdiqlandi va botga ulandi! ✅\n\n"
                    f"• <b>Foydalanuvchi logini:</b> {local_user.username}\n"
                    f"• <b>Tizimdagi rolingiz:</b> {local_role}\n"
                    f"• <b>Tasdiqlangan telefon:</b> {formatted_phone}\n\n"
                    f"Endi barcha xizmat xabarnomalari, yangi murojaatlar, ijro statuslari va "
                    f"navbat talonlari to'g'ridan-to'g'ri ushbu bot orqali yetkaziladi."
                )
                await TelegramService.send_telegram_message(
                    chat_id=chat_id,
                    text=success_msg,
                    reply_markup={"remove_keyboard": True}
                )
                return

            # -----------------------------------------------------------------
            # 2-BOSQICH: Agar mahalliy bazada telefon topilmasa -> HEMIS API orqali
            # universitet talabalar bazasidan tekshirish (fallback).
            # -----------------------------------------------------------------
            res = await TelegramService.validate_phone_with_jbnuu(formatted_phone)

            if res.get("success") is True:
                data = res.get("data", {})
                emp_id_num = data.get("employee_id_number")
                raw_id = str(data.get("id")) if data.get("id") else None

                # Bazamizdan talaba foydalanuvchisini qidirish
                conditions = []
                if emp_id_num:
                    conditions.append(User.hemis_student_id == str(emp_id_num))
                    conditions.append(User.username == str(emp_id_num))
                if raw_id:
                    conditions.append(User.hemis_student_id == raw_id)
                conditions.append(User.phone == formatted_phone)

                stmt = select(User).where(or_(*conditions))
                matched_user = (await db.execute(stmt)).scalars().first()

                if matched_user:
                    matched_user.telegram_chat_id = chat_id
                    matched_user.telegram_username = username
                    matched_user.telegram_connected_at = datetime.now(timezone.utc)
                    matched_user.phone = formatted_phone
                    await db.commit()

                    matched_role = getattr(matched_user.role, "value", str(matched_user.role))
                    success_msg = (
                        f"🎉 <b>Hurmatli {matched_user.full_name}!</b>\n\n"
                        f"Universitet HEMIS tizimi orqali telefon raqamingiz muvaffaqiyatli tasdiqlandi va "
                        f"profilingiz botga ulandi! ✅\n\n"
                        f"• <b>Foydalanuvchi:</b> {matched_user.username}\n"
                        f"• <b>Rol:</b> {matched_role}\n"
                        f"• <b>Telefon:</b> {formatted_phone}\n\n"
                        f"Endi har bir murojaatingiz ko'rib chiqilishi, javob matni va "
                        f"darcha qabuli talonlari shu yerga yetkaziladi."
                    )
                    await TelegramService.send_telegram_message(
                        chat_id=chat_id,
                        text=success_msg,
                        reply_markup={"remove_keyboard": True}
                    )
                else:
                    # HEMISda bor, lekin mahalliy bazada hali ro'yxatdan o'tmagan
                    info_msg = (
                        f"Telefon raqamingiz ({formatted_phone}) universitet bazasida tasdiqlandi, "
                        f"lekin Registrator ofisi portalida profilingiz hali yaratilmagan.\n\n"
                        f"Iltimos, avval veb-portal orqali tizimga kiring, shunda hisobingiz to'liq faollashadi."
                    )
                    await TelegramService.send_telegram_message(
                        chat_id=chat_id,
                        text=info_msg,
                        reply_markup={"remove_keyboard": True}
                    )
            else:
                # HEMISda ham, mahalliy xodimlar bazasida ham topilmadi
                err_msg = (
                    f"❌ Kechirasiz, <b>{formatted_phone}</b> telefon raqami Registrator ofisi "
                    f"xodimlari ro'yxatida ham, universitet HEMIS ma'lumotlar bazasida ham topilmadi.\n\n"
                    f"Iltimos, tizimda ro'yxatdan o'tgan yoki rasmiy telefon raqamingizdan foydalaning."
                )
                await TelegramService.send_telegram_message(chat_id, err_msg)
            return

        # 3. Har qanday boshqa matnli xabar
        help_msg = (
            "Registrator ofisi axborot tizimi botiga xush kelibsiz.\n\n"
            "Profilingizni ulash uchun /start buyrug'ini yuboring."
        )
        await TelegramService.send_telegram_message(chat_id, help_msg)


async def run_telegram_bot_poller():
    """Telegram Bot uzoq so'rov (long-polling) foni."""
    logger.info("Telegram bot poller ishga tushirilmoqda...")
    offset = 0

    while True:
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            # Token hali qo'yilmagan bo'lsa kutish
            await asyncio.sleep(10)
            continue

        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"offset": offset, "timeout": 20}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        try:
                            await handle_telegram_update(update)
                        except Exception as ex:
                            logger.error(f"Telegram update qayta ishlashda xatolik: {ex}")
                elif resp.status_code == 409:
                    logger.warning("Telegram bot poller 409 Conflict (boshqa instansiya yoki jarayon getUpdates bajarmoqda). 15 soniya kutilmoqda...")
                    await asyncio.sleep(15)
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 10))
                    logger.warning(f"Telegram API 429 Too Many Requests. {retry_after} soniya kutilmoqda...")
                    await asyncio.sleep(retry_after)
                elif resp.status_code == 401:
                    logger.warning("Telegram bot tokeni noto'g'ri (401 Unauthorized). Tekshirib ko'ring.")
                    await asyncio.sleep(30)
                else:
                    logger.warning(f"Telegram polling kutilmagan status: {resp.status_code}")
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Telegram bot poller to'xtatildi.")
            break
        except Exception as e:
            logger.debug(f"Telegram polling kutish xatosi: {e}")
            await asyncio.sleep(5)
