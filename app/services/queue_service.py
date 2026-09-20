import uuid
from datetime import datetime, timezone, timedelta, date, time
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Appointment, AppointmentStatus, Service, User, UserRole, Holiday
from app.services.kpi_service import KPIService


class QueueService:
    """Registrator ofisi elektron navbat (Darcha qabuli) boshqaruv xizmati."""

    SLOT_MINUTES = 15
    WORK_START_HOUR = 9
    WORK_END_HOUR = 17
    LUNCH_START_HOUR = 13
    LUNCH_END_HOUR = 14
    TASHKENT_TZ = timezone(timedelta(hours=5))

    @classmethod
    def get_now(cls) -> datetime:
        """Toshkent vaqti bo'yicha joriy datetime."""
        return datetime.now(cls.TASHKENT_TZ)

    @classmethod
    def generate_slots(cls) -> List[Tuple[time, time]]:
        """Ish kuni uchun barcha 15 daqiqalik qabul oraliqlarini hisoblaydi."""
        slots = []
        # Ertalabki seans: 09:00 - 13:00
        cur_min = cls.WORK_START_HOUR * 60
        lunch_min = cls.LUNCH_START_HOUR * 60
        while cur_min < lunch_min:
            s_hour, s_min = divmod(cur_min, 60)
            e_hour, e_min = divmod(cur_min + cls.SLOT_MINUTES, 60)
            slots.append((time(s_hour, s_min), time(e_hour, e_min)))
            cur_min += cls.SLOT_MINUTES

        # Tushdan keyingi seans: 14:00 - 17:00
        cur_min = cls.LUNCH_END_HOUR * 60
        end_min = cls.WORK_END_HOUR * 60
        while cur_min < end_min:
            s_hour, s_min = divmod(cur_min, 60)
            e_hour, e_min = divmod(cur_min + cls.SLOT_MINUTES, 60)
            slots.append((time(s_hour, s_min), time(e_hour, e_min)))
            cur_min += cls.SLOT_MINUTES

        return slots

    @classmethod
    def slot_to_str(cls, start: time, end: time) -> str:
        return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

    @classmethod
    def parse_slot_str(cls, slot_str: str) -> Tuple[time, time]:
        """ '09:00 - 09:15' formatini (time(9,0), time(9,15)) ga aylantiradi."""
        parts = slot_str.split("-")
        if len(parts) != 2:
            raise ValueError("Noto'g'ri slot formati")
        s = datetime.strptime(parts[0].strip(), "%H:%M").time()
        e = datetime.strptime(parts[1].strip(), "%H:%M").time()
        return s, e

    # Backward compatibility uchun ro'yxat
    DEFAULT_SLOTS = [
        "09:00 - 09:15", "09:15 - 09:30", "09:30 - 09:45", "09:45 - 10:00",
        "10:00 - 10:15", "10:15 - 10:30", "10:30 - 10:45", "10:45 - 11:00",
        "11:00 - 11:15", "11:15 - 11:30", "11:30 - 11:45", "11:45 - 12:00",
        "12:00 - 12:15", "12:15 - 12:30", "12:30 - 12:45", "12:45 - 13:00",
        # Lunch 13:00 - 14:00
        "14:00 - 14:15", "14:15 - 14:30", "14:30 - 14:45", "14:45 - 15:00",
        "15:00 - 15:15", "15:15 - 15:30", "15:30 - 15:45", "15:45 - 16:00",
        "16:00 - 16:15", "16:15 - 16:30", "16:30 - 16:45", "16:45 - 17:00"
    ]

    @classmethod
    async def is_working_day(cls, db: AsyncSession, target_date: date) -> Tuple[bool, Optional[str]]:
        """Sana dam olish kuni yoki rasmiy bayram ekanligini aniqlaydi."""
        # 1. Yakshanba tekshiruvi
        if target_date.weekday() == 6:
            return False, "Yakshanba — rasmiy dam olish kuni. Qabul dushanba-shanba kunlari 09:00 dan 17:00 gacha amalga oshiriladi."

        # 2. Kalendar bayram tekshiruvi
        date_str = target_date.strftime("%Y-%m-%d")
        stmt = select(Holiday).where(Holiday.holiday_date == date_str, Holiday.is_working_day == False)
        holiday = (await db.execute(stmt)).scalars().first()
        if holiday:
            return False, f"Ushbu sana rasmiy dam olish kuni: {holiday.title}"

        return True, None

    @classmethod
    async def find_next_available_date(cls, db: AsyncSession, start_date: date) -> date:
        """Berilgan sanadan boshlab eng yaqin haqiqiy ish kunini topadi."""
        check_date = start_date
        for _ in range(14):  # 2 haftagacha qidirish
            is_work, _ = await cls.is_working_day(db, check_date)
            if is_work:
                return check_date
            check_date += timedelta(days=1)
        return start_date

    @classmethod
    async def get_available_slots(
        cls,
        db: AsyncSession,
        appointment_date: str,
        service_id: int,
        student_id: Optional[int] = None
    ) -> List[str]:
        """Mavjud bo'sh vaqt slotlari (stringlar ro'yxati, backward-compatible)."""
        res = await cls.get_detailed_slots(db, appointment_date, service_id, student_id=student_id)
        if not res.get("is_working_day"):
            return []
        return [s["time_slot"] for s in res.get("slots", []) if s.get("is_available")]

    @classmethod
    async def get_detailed_slots(
        cls,
        db: AsyncSession,
        appointment_date: str,
        service_id: int,
        student_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Belgilangan sana uchun qabul vaqtlarini to'liq va tabiiy tahlil qiladi.
        O'tgan vaqtlar va band qilingan vaqtlar aniq holat bilan qaytariladi.
        Kunduzgi ta'lim shaklidagi talabalar uchun kelgusi kunlarga oldindan navbat olish cheklanadi.
        """
        now = cls.get_now()
        today = now.date()
        today_str = today.strftime("%Y-%m-%d")

        try:
            target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak).")

        # Talabaning ta'lim shaklini aniqlash (Kunduzgi / Sirtqi / Masofaviy)
        is_kunduzgi = False
        if student_id:
            st_user = await db.get(User, student_id)
            if st_user and st_user.education_form and st_user.education_form.strip().lower() == "kunduzgi":
                is_kunduzgi = True

        # Kunduzgi talaba uchun: agar kelgusi sana so'ralsa, darhol cheklov bildirishnomasi qaytariladi
        if is_kunduzgi and target_date > today:
            return {
                "date": appointment_date,
                "is_working_day": False,
                "is_today": False,
                "is_kunduzgi": True,
                "current_time": now.strftime("%H:%M"),
                "total_available": 0,
                "morning_available": 0,
                "afternoon_available": 0,
                "message": "Kunduzgi ta'lim shakli talabalari elektron navbatni faqat joriy kun (bugun) uchun olishlari mumkin. Oldindan (kelgusi sanalarga) navbat olish taqiqlangan.",
                "next_available_date": None,
                "slots": []
            }

        # Ish kuni tekshiruvi
        is_work, holiday_msg = await cls.is_working_day(db, target_date)
        if not is_work:
            return {
                "date": appointment_date,
                "is_working_day": False,
                "is_today": (target_date == today),
                "is_kunduzgi": is_kunduzgi,
                "current_time": now.strftime("%H:%M"),
                "total_available": 0,
                "morning_available": 0,
                "afternoon_available": 0,
                "message": holiday_msg,
                "next_available_date": None if is_kunduzgi else (await cls.find_next_available_date(db, target_date + timedelta(days=1))).strftime("%Y-%m-%d"),
                "slots": []
            }

        # Band qilingan slotlarni olish
        stmt = select(Appointment.time_slot).where(
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])
        )
        booked_slots = set((await db.execute(stmt)).scalars().all())

        is_past_day = (target_date < today)
        is_today = (target_date == today)
        current_time = now.time()

        all_slots = cls.generate_slots()
        slots_list = []
        available_count = 0
        morning_available = 0
        afternoon_available = 0

        for start_t, end_t in all_slots:
            slot_str = cls.slot_to_str(start_t, end_t)
            is_morning = start_t.hour < cls.LUNCH_START_HOUR

            if is_past_day:
                slots_list.append({
                    "time_slot": slot_str,
                    "start_time": start_t.strftime("%H:%M"),
                    "end_time": end_t.strftime("%H:%M"),
                    "session": "morning" if is_morning else "afternoon",
                    "is_available": False,
                    "status": "past",
                    "reason": "Sana o'tib ketgan"
                })
            elif is_today and start_t <= current_time:
                slots_list.append({
                    "time_slot": slot_str,
                    "start_time": start_t.strftime("%H:%M"),
                    "end_time": end_t.strftime("%H:%M"),
                    "session": "morning" if is_morning else "afternoon",
                    "is_available": False,
                    "status": "past",
                    "reason": "Vaqt o'tib ketgan"
                })
            elif slot_str in booked_slots:
                slots_list.append({
                    "time_slot": slot_str,
                    "start_time": start_t.strftime("%H:%M"),
                    "end_time": end_t.strftime("%H:%M"),
                    "session": "morning" if is_morning else "afternoon",
                    "is_available": False,
                    "status": "booked",
                    "reason": "Band qilingan"
                })
            else:
                slots_list.append({
                    "time_slot": slot_str,
                    "start_time": start_t.strftime("%H:%M"),
                    "end_time": end_t.strftime("%H:%M"),
                    "session": "morning" if is_morning else "afternoon",
                    "is_available": True,
                    "status": "available",
                    "reason": "Bo'sh"
                })
                available_count += 1
                if is_morning:
                    morning_available += 1
                else:
                    afternoon_available += 1

        message = None
        next_date_str = None
        if is_past_day:
            message = "O'tib ketgan sana uchun navbat olib bo'lmaydi."
            next_date_str = None if is_kunduzgi else (await cls.find_next_available_date(db, today)).strftime("%Y-%m-%d")
        elif is_today and available_count == 0:
            message = "Bugungi kun uchun barcha qabul vaqtlari yakunlangan (qabul soatlari dushanba-shanba 09:00 dan 17:00 gacha)."
            next_date_str = None if is_kunduzgi else (await cls.find_next_available_date(db, today + timedelta(days=1))).strftime("%Y-%m-%d")

        return {
            "date": appointment_date,
            "is_working_day": True,
            "is_today": is_today,
            "is_kunduzgi": is_kunduzgi,
            "current_time": now.strftime("%H:%M"),
            "total_available": available_count,
            "morning_available": morning_available,
            "afternoon_available": afternoon_available,
            "message": message,
            "next_available_date": next_date_str,
            "slots": slots_list
        }

    @classmethod
    async def book_appointment(
        cls,
        db: AsyncSession,
        student_id: int,
        service_id: int,
        appointment_date: str,
        time_slot: str
    ) -> Appointment:
        """Talaba uchun elektron talon va navbat band qilish."""
        now = cls.get_now()
        today = now.date()
        today_str = today.strftime("%Y-%m-%d")

        # 1. Sana validatsiyasi
        try:
            target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak).")

        if target_date < today:
            raise HTTPException(status_code=400, detail="O'tib ketgan sanaga navbat olib bo'lmaydi.")

        # Talaba profilini tekshirish
        student = await db.get(User, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Talaba foydalanuvchisi topilmadi.")

        is_kunduzgi = bool(student.education_form and student.education_form.strip().lower() == "kunduzgi")

        # Kunduzgi ta'lim talabasi uchun qat'iy cheklov: navbat faqat joriy kun (bugun) uchun olinishi lozim!
        if is_kunduzgi and target_date != today:
            raise HTTPException(
                status_code=400,
                detail="Kunduzgi ta'lim shakli talabalari elektron navbatni faqat joriy kun (bugun) uchun olishlari mumkin. Oldindan (kelgusi sanalarga) navbat olish taqiqlangan."
            )

        # Har qanday talaba uchun uzoq kelajak sanalarini cheklash (maksimal 14 kun)
        if target_date > today + timedelta(days=14):
            raise HTTPException(
                status_code=400,
                detail="Navbatni ko'pi bilan 14 kun oldindan band qilish mumkin."
            )

        # 2. Ish kuni va bayram tekshiruvi
        is_work, holiday_msg = await cls.is_working_day(db, target_date)
        if not is_work:
            raise HTTPException(status_code=400, detail=holiday_msg or "Dam olish kuni.")

        # 3. Vaqt oralig'ini tekshirish
        try:
            start_t, end_t = cls.parse_slot_str(time_slot)
        except ValueError:
            raise HTTPException(status_code=400, detail="Vaqt oralig'i formati noto'g'ri (HH:MM - HH:MM bo'lishi kerak).")

        # 4. Bugun uchun vaqt o'tganligini toza DateTime bilan tekshirish
        scheduled_start_dt = datetime.combine(target_date, start_t).replace(tzinfo=cls.TASHKENT_TZ)
        scheduled_end_dt = datetime.combine(target_date, end_t).replace(tzinfo=cls.TASHKENT_TZ)

        if scheduled_start_dt <= now:
            raise HTTPException(
                status_code=400,
                detail="Tanlangan vaqt oralig'i o'tib ketgan. Iltimos, joriy vaqtdan keyingi bo'sh vaqtni tanlang."
            )

        # 5. Anti-Abuse: Bitta talaba ayni bir kunda bitta xizmat bo'yicha faqat 1 ta faol navbatga ega bo'lishi mumkin
        student_active_stmt = select(Appointment).where(
            Appointment.student_id == student_id,
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])
        )
        student_active = (await db.execute(student_active_stmt)).scalars().first()
        if student_active:
            raise HTTPException(
                status_code=400,
                detail=f"Sizda ushbu sana uchun mazkur xizmat bo'yicha allaqachon faol navbat taloni mavjud (#{student_active.ticket_code}, vaqti: {student_active.time_slot})."
            )

        # 5.1. No-Show tekshiruvi: so'nggi 7 kunda 3 marta kelmagan talabalarga vaqtinchalik 3 kunlik blokirovka
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        no_show_stmt = select(func.count(Appointment.id)).where(
            Appointment.student_id == student_id,
            Appointment.status == AppointmentStatus.NO_SHOW,
            Appointment.created_at >= seven_days_ago
        )
        no_show_count = (await db.execute(no_show_stmt)).scalar() or 0
        if no_show_count >= 3:
            raise HTTPException(
                status_code=403,
                detail="Siz so'nggi 7 kun ichida 3 marta belgilangan navbatingizga kelmagansiz (No-Show). Intizomiy qoidalar bo'yicha navbat olish 3 kunga vaqtincha cheklangan. Xizmat olish uchun Registrator ofisi darchalariga bevosita kelib murojaat qilishingiz mumkin."
            )

        # 5.2. Kunlik global limit: bitta talaba bir kunda barcha xizmatlar bo'yicha jami ko'pi bilan 3 ta navbat taloni olishi mumkin
        daily_count_stmt = select(func.count(Appointment.id)).where(
            Appointment.student_id == student_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_SERVICE])
        )
        daily_total = (await db.execute(daily_count_stmt)).scalar() or 0
        if daily_total >= 3:
            raise HTTPException(
                status_code=400,
                detail="Kunlik navbat limiti tugadi. Bitta talaba bir kunda barcha xizmatlar bo'yicha ko'pi bilan 3 ta navbat taloni olishi mumkin."
            )

        # 6. Double-booking tekshiruvi (poyga holati - Race condition himoyasi)
        stmt = select(Appointment).where(
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.time_slot == time_slot,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_SERVICE])
        )
        try:
            bind = db.get_bind()
            if bind and getattr(bind, "dialect", None) and bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update()
        except Exception:
            pass

        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(status_code=409, detail="Ushbu vaqt oralig'i allaqachon band qilingan (boshqa talaba tomonidan).")

        # Xizmat va darcha ma'lumotlarini olish
        service = await db.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Tanlangan xizmat topilmadi.")

        window_str = "104-xona, 1-darcha"
        if service.department and service.department.window_number:
            window_str = f"104-xona, {service.department.window_number}"

        staff_stmt = select(User).where(
            User.department_id == service.department_id,
            User.role.in_([UserRole.FRONT_STAFF, UserRole.BACK_STAFF]),
            User.is_active == True
        )
        staff_member = (await db.execute(staff_stmt)).scalars().first()
        staff_id = staff_member.id if staff_member else None

        # Talon kodi generatsiyasi: TALON-MMDD-XXXX
        date_tag = appointment_date.replace("-", "")[4:]
        unique_suffix = uuid.uuid4().hex[:4].upper()
        ticket_code = f"TALON-{date_tag}-{unique_suffix}"

        appointment = Appointment(
            ticket_code=ticket_code,
            student_id=student_id,
            service_id=service_id,
            staff_id=staff_id,
            window_number=window_str,
            appointment_date=appointment_date,
            time_slot=time_slot,
            scheduled_start=scheduled_start_dt.astimezone(timezone.utc),
            scheduled_end=scheduled_end_dt.astimezone(timezone.utc),
            status=AppointmentStatus.BOOKED,
            earned_kpi_points=service.kpi_points
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)
        return appointment

    @classmethod
    async def complete_appointment(
        cls, db: AsyncSession, appointment_id: int, staff_id: int, notes: Optional[str] = None
    ) -> Appointment:
        """Xizmat ko'rsatishni yakunlash va KPI ballini hisoblash."""
        appointment = await db.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Qabul ma'lumoti topilmadi.")

        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = datetime.now(timezone.utc)
        appointment.staff_id = staff_id
        if notes:
            appointment.notes = notes

        # Xodimga KPI ballini yozish
        await KPIService.record_completed_service(
            db=db,
            employee_id=staff_id,
            kpi_points=appointment.earned_kpi_points,
            is_appointment=True
        )

        await db.commit()
        await db.refresh(appointment)
        return appointment

    @classmethod
    async def cancel_appointment(
        cls, db: AsyncSession, appointment_id: int, student_id: int
    ) -> Appointment:
        """Talaba kelolmagan taqdirda o'z navbatini bekor qiladi va slot bo'shaydi."""
        appointment = await db.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Navbat taloni topilmadi.")
        if appointment.student_id != student_id:
            raise HTTPException(status_code=403, detail="Faqat o'z navbat talonini bekor qilish mumkin.")
        if appointment.status != AppointmentStatus.BOOKED:
            raise HTTPException(
                status_code=400,
                detail=f"Faqat kutilayotgan navbatni bekor qilish mumkin (joriy holat: {appointment.status.value})."
            )

        appointment.status = AppointmentStatus.CANCELLED
        await db.commit()
        await db.refresh(appointment)
        return appointment

    @classmethod
    async def auto_expire_no_show_appointments(cls, db: AsyncSession) -> int:
        """Yangi kunga o'tilganda o'tib ketgan barcha sanalardagi (appointment_date < today) navbatlarni tozalash."""
        now = cls.get_now()
        today_str = now.date().strftime("%Y-%m-%d")

        count = 0

        # O'tgan sanalar (appointment_date < today_str): barcha faol navbatlar (BOOKED, CHECKED_IN, IN_SERVICE)
        stmt_past = select(Appointment).where(
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_SERVICE]),
            Appointment.appointment_date < today_str
        )
        past_appointments = (await db.execute(stmt_past)).scalars().all()
        for app in past_appointments:
            if app.status == AppointmentStatus.IN_SERVICE:
                app.status = AppointmentStatus.COMPLETED
                app.completed_at = app.completed_at or app.called_at or datetime.now(timezone.utc)
                app.notes = (app.notes or "") + " [Avto-yakunlandi: Ish kuni tugagani sababli tizim tomonidan yakunlandi]"
            else:
                app.status = AppointmentStatus.NO_SHOW
                app.notes = (app.notes or "") + " [Avto-yopildi: Talaba belgilangan kunda kelmadi (No-Show)]"
            count += 1

        if count > 0:
            await db.commit()
        return count

    @classmethod
    async def call_appointment(
        cls, db: AsyncSession, appointment_id: int, staff: User
    ) -> Appointment:
        """Talabani darchaga chaqirish (holatni IN_SERVICE ga o'tkazish, called_at ni belgilash)."""
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.student)
            )
            .where(Appointment.id == appointment_id)
        )
        result = await db.execute(stmt)
        appointment = result.scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=404, detail="Navbat taloni topilmadi.")

        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise HTTPException(
                status_code=400,
                detail=f"Ushbu navbat yakunlangan yoki bekor qilingan (holat: {appointment.status.value})."
            )

        appointment.status = AppointmentStatus.IN_SERVICE
        appointment.called_at = datetime.now(timezone.utc)
        appointment.staff_id = staff.id

        # Agar xodimning bo'limida darcha raqami bo'lsa, darchani moslashtirish
        if staff.department and staff.department.window_number:
            appointment.window_number = staff.department.window_number

        await db.commit()
        await db.refresh(appointment)

        # Telegram va tizim xabarnomasi (navbati darchaga chaqirilganligi haqida)
        try:
            if appointment.student and appointment.student.telegram_chat_id:
                from app.services.telegram_service import TelegramService
                call_msg = (
                    f"🔔 <b>Sizning navbatingiz keldi!</b>\n\n"
                    f"Hurmatli <b>{appointment.student.full_name}</b>!\n"
                    f"Sizning <b>#{appointment.ticket_code}</b> raqamli navbatingiz darchaga chaqirildi.\n\n"
                    f"• <b>Darcha:</b> {appointment.window_number}\n"
                    f"• <b>Xizmat:</b> {appointment.service.title if appointment.service else 'Registrator xizmati'}\n\n"
                    f"<i>Iltimos, darhol belgilangan darchaga yaqinlashing.</i>"
                )
                await TelegramService.send_telegram_message(appointment.student.telegram_chat_id, call_msg)
        except Exception:
            pass

        return appointment

    @classmethod
    async def get_live_board_data(cls, db: AsyncSession) -> Dict[str, Any]:
        """Kutish zali katta ekrani (TV Display) uchun jonli navbat ma'lumotlarini to'plash."""
        now_tz = cls.get_now()
        today_str = now_tz.date().strftime("%Y-%m-%d")

        # Eskirgan yoki o'tib ketgan navbatlarni yangi kunda tozalash
        try:
            await cls.auto_expire_no_show_appointments(db)
        except Exception:
            pass

        # 1. Bugungi barcha faol navbatlar
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.service),
                selectinload(Appointment.student)
            )
            .where(Appointment.appointment_date == today_str)
            .order_by(Appointment.time_slot.asc(), Appointment.id.asc())
        )
        all_today = (await db.execute(stmt)).scalars().all()

        # 2. Hozir chaqirilayotgan yoki xizmat ko'rsatilayotganlar (IN_SERVICE)
        in_service_list = [
            a for a in all_today if a.status == AppointmentStatus.IN_SERVICE
        ]
        in_service_list.sort(
            key=lambda x: x.called_at or x.created_at,
            reverse=True
        )

        # Asosiy qahramon (eng oxirgi chaqirilgan talon)
        latest_called = None
        if in_service_list:
            top = in_service_list[0]
            latest_called = {
                "id": top.id,
                "ticket_code": top.ticket_code,
                "window_number": top.window_number,
                "service_title": top.service.title if top.service else "Registrator xizmati",
                "student_name": top.student.full_name if top.student else "Talaba",
                "time_slot": top.time_slot,
                "called_at": top.called_at.isoformat() if top.called_at else top.created_at.isoformat()
            }

        # Darchalar bo'yicha faol xizmatlar (Active windows map)
        active_windows = []
        seen_windows = set()
        for a in in_service_list:
            w = a.window_number or "1-darcha"
            if w not in seen_windows:
                seen_windows.add(w)
                active_windows.append({
                    "id": a.id,
                    "window_number": w,
                    "ticket_code": a.ticket_code,
                    "service_title": a.service.title if a.service else "Registrator xizmati",
                    "student_name": a.student.full_name if a.student else "Talaba",
                    "called_at": a.called_at.isoformat() if a.called_at else a.created_at.isoformat()
                })

        # Kutish zalidagi navbatdagilar (CHECKED_IN birinchi, keyin BOOKED)
        waiting_checked_in = [a for a in all_today if a.status == AppointmentStatus.CHECKED_IN]
        waiting_booked = [a for a in all_today if a.status == AppointmentStatus.BOOKED]
        waiting_combined = waiting_checked_in + waiting_booked

        waiting_queue = [
            {
                "id": a.id,
                "ticket_code": a.ticket_code,
                "window_number": a.window_number,
                "service_title": a.service.title if a.service else "Registrator xizmati",
                "time_slot": a.time_slot,
                "status": a.status.value,
                "is_arrived": a.status == AppointmentStatus.CHECKED_IN
            }
            for a in waiting_combined[:12]
        ]

        # Bugungi statistika
        total_count = len(all_today)
        completed_count = len([a for a in all_today if a.status == AppointmentStatus.COMPLETED])
        in_service_count = len(in_service_list)
        waiting_count = len(waiting_combined)

        return {
            "today_date": today_str,
            "server_time": now_tz.isoformat(),
            "latest_called": latest_called,
            "in_service_list": [
                {
                    "id": a.id,
                    "ticket_code": a.ticket_code,
                    "window_number": a.window_number,
                    "service_title": a.service.title if a.service else "Registrator xizmati",
                    "student_name": a.student.full_name if a.student else "Talaba",
                    "called_at": a.called_at.isoformat() if a.called_at else a.created_at.isoformat()
                }
                for a in in_service_list[:6]
            ],
            "active_windows": active_windows,
            "waiting_queue": waiting_queue,
            "stats": {
                "total_today": total_count,
                "completed_today": completed_count,
                "in_service_count": in_service_count,
                "waiting_count": waiting_count
            }
        }
