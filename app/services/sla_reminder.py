"""
SLA Deadline Reminder Service
Fon vazifasi: har 15 daqiqada SLA muddati yaqinlashayotgan
murojaatlar bo'yicha xodimga Telegram eslatma yuboradi.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models import Appeal, AppealStatus, User, Appointment, AppointmentStatus
from app.services.telegram_service import TelegramService

from app.services.appeal_service import AppealService
from app.services.queue_service import QueueService
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)

# Necha soat qolganida eslatma yuboriladi
REMINDER_THRESHOLD_HOURS = 2
# Bir murojaatga necha marta eslatma yuborilishi mumkin (shu sessiyada)
_reminded_set: set = set()
# Bir navbatga necha marta eslatma yuborilishi mumkin (shu sessiyada)
_reminded_appointments_set: set = set()
_last_backup_cleanup: Optional[datetime] = None


async def check_and_send_sla_reminders(db: Optional[AsyncSession] = None):
    """SLA muddati REMINDER_THRESHOLD_HOURS soatdan kam qolgan barcha
    ochiq murojaatlar uchun biriktirilgan xodimga Telegram eslatma yuboradi.
    Shuningdek, 72 soat ichida tasdiqlanmagan murojaatlarni avtomatik yopadi va
    kelinmagan o'tib ketgan elektron navbatlarni NO_SHOW holatiga o'tkazadi."""
    if db is not None:
        await _process_sla_reminders(db)
    else:
        async with AsyncSessionLocal() as session:
            await _process_sla_reminders(session)


async def _process_sla_reminders(db: AsyncSession):
    now = datetime.now(timezone.utc)
    threshold_dt = now + timedelta(hours=REMINDER_THRESHOLD_HOURS)

    try:
        # 1. 72 soatlik tasdiqlash muddati o'tgan murojaatlarni avtomatik yopish
        closed_count = await AppealService.auto_close_expired(db)
        if closed_count > 0:
            logger.info(f"72 soatlik muddat o'tgan {closed_count} ta murojaat avtomatik yopildi.")

        # 2. Kelinmagan o'tib ketgan elektron navbatlarni NO_SHOW holatiga o'tkazish
        no_show_count = await QueueService.auto_expire_no_show_appointments(db)
        if no_show_count > 0:
            logger.info(f"{no_show_count} ta o'tib ketgan navbat taloni NO_SHOW holatiga o'tkazildi.")

        # 3. 30 kundan oshgan eski zaxira nusxalarini tozalash (har 6 soatda bir marta)
        global _last_backup_cleanup
        if _last_backup_cleanup is None or (now - _last_backup_cleanup) > timedelta(hours=6):
            deleted_backups = BackupService.cleanup_old_backups(days=30)
            _last_backup_cleanup = now
            if deleted_backups > 0:
                logger.info(f"Davriy tozalash: {deleted_backups} ta eski zaxira arxivi o'chirildi.")

        # 4. SLA muddati tugayotgan arizalarni eslatish
        stmt = (
            select(Appeal)
            .options(selectinload(Appeal.service))
            .where(
                Appeal.status.in_([
                    AppealStatus.ASSIGNED,
                    AppealStatus.IN_PROGRESS,
                    AppealStatus.CLARIFICATION_NEEDED
                ]),
                Appeal.assigned_staff_id.isnot(None),
                Appeal.sla_deadline_at.isnot(None),
                Appeal.sla_deadline_at <= threshold_dt,
                Appeal.sla_deadline_at >= now  # Hali o'tmagan
            )
        )
        result = await db.execute(stmt)
        overdue_appeals = result.scalars().all()

        current_active_ids = {a.id for a in overdue_appeals}
        # Xotirani tozalash: faol bo'lmagan id larni set dan olib tashlash
        global _reminded_set
        _reminded_set = _reminded_set.intersection(current_active_ids)

        for appeal in overdue_appeals:
            # Bir sessiyada bir xil murojaatga qayta eslatma yubormaslik
            if appeal.id in _reminded_set:
                continue

            staff = await db.get(User, appeal.assigned_staff_id)
            if not staff or not staff.telegram_chat_id:
                continue

            deadline_local = appeal.sla_deadline_at
            minutes_left = int((deadline_local - now).total_seconds() / 60)
            hours_left = minutes_left // 60
            mins_left = minutes_left % 60

            time_str = f"{hours_left} soat {mins_left} daqiqa" if hours_left > 0 else f"{mins_left} daqiqa"

            msg = (
                f"⚠️ <b>SLA muddati yaqinlashmoqda!</b>\n\n"
                f"Hurmatli {staff.full_name},\n"
                f"Sizga biriktirilgan murojaatni ijro etish muddati <b>{time_str}</b> ichida tugaydi:\n\n"
                f"• <b>Talon:</b> #{appeal.ticket_number}\n"
                f"• <b>Mavzu:</b> {appeal.subject}\n"
                f"• <b>Xizmat:</b> {appeal.service.title if appeal.service else '-'}\n"
                f"• <b>SLA muddati:</b> {deadline_local.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"<i>Iltimos, o'z vaqtida ijro etilib, natijani tizimga yuklang. "
                f"Muddatni o'tkazib yuborish KPI ko'rsatkichingizga salbiy ta'sir qiladi.</i>"
            )

            sent = await TelegramService.send_telegram_message(
                chat_id=staff.telegram_chat_id,
                text=msg
            )
            if sent:
                _reminded_set.add(appeal.id)
                logger.info(
                    f"SLA eslatma yuborildi: murojaat #{appeal.ticket_number} "
                    f"-> xodim {staff.full_name} (TG: {staff.telegram_chat_id})"
                )

        # 4. Bugungi darcha qabuliga 10-45 daqiqa qolgan talabalarga eslatma
        now_utc = datetime.now(timezone.utc)
        now_tashkent = QueueService.get_now()
        dates_to_check = list({now_utc.strftime("%Y-%m-%d"), now_tashkent.strftime("%Y-%m-%d")})

        start_utc = now_utc + timedelta(minutes=10)
        end_utc = now_utc + timedelta(minutes=45)
        start_tashkent = now_tashkent + timedelta(minutes=10)
        end_tashkent = now_tashkent + timedelta(minutes=45)

        appt_stmt = (
            select(Appointment)
            .options(selectinload(Appointment.student), selectinload(Appointment.service))
            .where(
                Appointment.appointment_date.in_(dates_to_check),
                Appointment.status == AppointmentStatus.BOOKED,
                Appointment.scheduled_start.isnot(None),
                or_(
                    and_(Appointment.scheduled_start >= start_utc, Appointment.scheduled_start <= end_utc),
                    and_(Appointment.scheduled_start >= start_tashkent, Appointment.scheduled_start <= end_tashkent)
                )
            )
        )
        appts_to_remind = (await db.execute(appt_stmt)).scalars().all()

        global _reminded_appointments_set
        active_appt_ids = {ap.id for ap in appts_to_remind}
        _reminded_appointments_set = _reminded_appointments_set.intersection(active_appt_ids)

        for appt in appts_to_remind:
            if appt.id in _reminded_appointments_set:
                continue
            if appt.student and appt.student.telegram_chat_id:
                sent = await TelegramService.notify_appointment_reminder(
                    student_chat_id=appt.student.telegram_chat_id,
                    ticket_code=appt.ticket_code,
                    window_number=appt.window_number,
                    time_slot=appt.time_slot,
                    service_title=appt.service.title if appt.service else "Elektron navbat"
                )
                if sent:
                    _reminded_appointments_set.add(appt.id)
                    logger.info(
                        f"Navbat eslatmasi yuborildi: talon #{appt.ticket_code} "
                        f"-> talaba {appt.student.full_name} (TG: {appt.student.telegram_chat_id})"
                    )

    except Exception as e:
        logger.error(f"SLA reminder tekshirishda xatolik: {e}")


async def run_sla_reminder_loop():
    """Har 2 daqiqada SLA deadline eslatmalarini va avto-yopilishni tekshirib turuvchi fon vazifasi."""
    logger.info("SLA Reminder va Auto-Close xizmati ishga tushirildi (har 2 daqiqada tekshiriladi).")
    while True:
        try:
            await check_and_send_sla_reminders()
        except asyncio.CancelledError:
            logger.info("SLA Reminder xizmati to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"SLA reminder loop xatosi: {e}")
        await asyncio.sleep(120)  # Har 2 daqiqa (120 soniya)

