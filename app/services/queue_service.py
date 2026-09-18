import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Appointment, AppointmentStatus, Service, User, UserRole
from app.services.kpi_service import KPIService


class QueueService:
    # 15-minute slots between 09:00 and 17:00, excluding 13:00-14:00 lunch
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
    async def get_available_slots(
        cls, db: AsyncSession, appointment_date: str, service_id: int
    ) -> List[str]:
        """Get remaining free 15-minute slots for the given date and service, excluding past slots if today."""
        tashkent_tz = timezone(timedelta(hours=5))
        now_local = datetime.now(tashkent_tz)
        today_str = now_local.strftime("%Y-%m-%d")

        # 1. Past date & Sunday check
        try:
            dt = datetime.strptime(appointment_date, "%Y-%m-%d")
            if appointment_date < today_str:
                return []
            if dt.weekday() == 6:  # Sunday
                return []
        except ValueError:
            raise HTTPException(status_code=400, detail="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak).")

        # 2. Holiday check
        from app.models import Holiday
        holiday_stmt = select(Holiday).where(Holiday.holiday_date == appointment_date, Holiday.is_working_day == False)
        holiday = (await db.execute(holiday_stmt)).scalars().first()
        if holiday:
            return []

        # 3. Fetch already booked slots
        stmt = select(Appointment.time_slot).where(
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])
        )
        result = await db.execute(stmt)
        booked_slots = set(result.scalars().all())

        # 4. Filter out booked slots and past slots for today
        is_today = (appointment_date == today_str)
        current_time = now_local.time()

        available_slots = []
        for slot in cls.DEFAULT_SLOTS:
            if slot in booked_slots:
                continue
            if is_today:
                slot_start_str = slot.split(" - ")[0].strip()
                slot_time = datetime.strptime(slot_start_str, "%H:%M").time()
                # O'tib ketgan vaqt oralig'ini chiqarib tashlash
                if slot_time <= current_time:
                    continue
            available_slots.append(slot)

        return available_slots

    @classmethod
    async def get_detailed_slots(
        cls, db: AsyncSession, appointment_date: str, service_id: int
    ) -> dict:
        """Belgilangan sana uchun har bir 15 daqiqalik vaqt oralig'ining aniq holatini (mavjud, o'tib ketgan, band) qaytaradi."""
        tashkent_tz = timezone(timedelta(hours=5))
        now_local = datetime.now(tashkent_tz)
        today_str = now_local.strftime("%Y-%m-%d")

        try:
            dt = datetime.strptime(appointment_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak).")

        # 1. Yakshanba tekshiruvi
        if dt.weekday() == 6:
            return {
                "date": appointment_date,
                "is_working_day": False,
                "message": "Yakshanba — rasmiy dam olish kuni. Qabul dushanba-shanba kunlari 09:00 dan 17:00 gacha amalga oshiriladi.",
                "slots": []
            }

        # 2. Bayram yoki dam olish kuni tekshiruvi
        from app.models import Holiday
        holiday_stmt = select(Holiday).where(Holiday.holiday_date == appointment_date, Holiday.is_working_day == False)
        holiday = (await db.execute(holiday_stmt)).scalars().first()
        if holiday:
            return {
                "date": appointment_date,
                "is_working_day": False,
                "message": f"Ushbu sana rasmiy dam olish kuni: {holiday.title}",
                "slots": []
            }

        # 3. Band qilingan slotlar
        stmt = select(Appointment.time_slot).where(
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])
        )
        result = await db.execute(stmt)
        booked_slots = set(result.scalars().all())

        is_past_date = (appointment_date < today_str)
        is_today = (appointment_date == today_str)
        current_time = now_local.time()

        slots_list = []
        available_count = 0

        for slot in cls.DEFAULT_SLOTS:
            slot_start_str = slot.split(" - ")[0].strip()
            slot_time = datetime.strptime(slot_start_str, "%H:%M").time()

            if is_past_date:
                slots_list.append({
                    "time_slot": slot,
                    "is_available": False,
                    "status": "past",
                    "reason": "Sana o'tib ketgan"
                })
            elif is_today and slot_time <= current_time:
                slots_list.append({
                    "time_slot": slot,
                    "is_available": False,
                    "status": "past",
                    "reason": "Vaqt o'tib ketgan"
                })
            elif slot in booked_slots:
                slots_list.append({
                    "time_slot": slot,
                    "is_available": False,
                    "status": "booked",
                    "reason": "Band qilingan"
                })
            else:
                slots_list.append({
                    "time_slot": slot,
                    "is_available": True,
                    "status": "available",
                    "reason": "Bo'sh"
                })
                available_count += 1

        message = None
        if is_past_date:
            message = "O'tib ketgan sana uchun navbat olib bo'lmaydi."
        elif is_today and available_count == 0:
            message = "Bugungi kun uchun barcha qabul vaqtlari yakunlangan (qabul soatlari 09:00 dan 17:00 gacha). Iltimos, keyingi ish kunini tanlang."

        return {
            "date": appointment_date,
            "is_working_day": True,
            "message": message,
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
        """Reserve an in-person appointment slot and generate electronic queue ticket."""
        tashkent_tz = timezone(timedelta(hours=5))
        now_local = datetime.now(tashkent_tz)
        today_str = now_local.strftime("%Y-%m-%d")

        # 1. Past date check
        if appointment_date < today_str:
            raise HTTPException(
                status_code=400,
                detail="O'tib ketgan sanaga navbat olib bo'lmaydi."
            )

        # 2. Sunday check
        try:
            dt = datetime.strptime(appointment_date, "%Y-%m-%d")
            if dt.weekday() == 6:  # Sunday
                raise HTTPException(
                    status_code=400,
                    detail="Yakshanba dam olish kuni. Qabul dushanbadan shanbagacha 09:00 dan 17:00 gacha amalga oshiriladi."
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak).")

        # 3. Holiday check
        from app.models import Holiday
        holiday_stmt = select(Holiday).where(Holiday.holiday_date == appointment_date, Holiday.is_working_day == False)
        holiday = (await db.execute(holiday_stmt)).scalars().first()
        if holiday:
            raise HTTPException(
                status_code=400,
                detail=f"Belgilangan sana rasmiy bayram yoki dam olish kuni: {holiday.title}"
            )

        if time_slot not in cls.DEFAULT_SLOTS:
            raise HTTPException(status_code=400, detail="Noto'g'ri vaqt oralig'i tanlandi.")

        # 4. Past time check for today (Bugungi kun uchun o'tib ketgan vaqt oralig'ini tekshirish)
        if appointment_date == today_str:
            slot_start_str = time_slot.split(" - ")[0].strip()
            slot_time = datetime.strptime(slot_start_str, "%H:%M").time()
            if slot_time <= now_local.time():
                raise HTTPException(
                    status_code=400,
                    detail="Tanlangan vaqt oralig'i o'tib ketgan. Iltimos, joriy vaqtdan keyingi bo'sh vaqtni tanlang."
                )

        # 5. Anti-Abuse: Bitta talaba ayni bir sana va xizmat bo'yicha faqat 1 ta faol navbatga ega bo'lishi mumkin
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

        # 6. Check double-booking for the same slot
        stmt = select(Appointment).where(
            Appointment.appointment_date == appointment_date,
            Appointment.service_id == service_id,
            Appointment.time_slot == time_slot,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN])
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(status_code=409, detail="Ushbu vaqt oralig'i allaqachon band qilingan.")

        # Get Service and Department to determine Window / Staff
        service = await db.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Tanlangan xizmat topilmadi.")

        window_str = "104-xona, 1-darcha"
        if service.department and service.department.window_number:
            window_str = f"104-xona, {service.department.window_number}"

        # Assign available staff member from department if available
        staff_stmt = select(User).where(
            User.department_id == service.department_id,
            User.role.in_([UserRole.FRONT_STAFF, UserRole.BACK_STAFF]),
            User.is_active == True
        )
        staff_member = (await db.execute(staff_stmt)).scalars().first()
        staff_id = staff_member.id if staff_member else None

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
        """Mark in-person appointment as completed and award KPI points to staff."""
        appointment = await db.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Qabul ma'lumoti topilmadi.")

        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = datetime.now(timezone.utc)
        appointment.staff_id = staff_id
        if notes:
            appointment.notes = notes

        # Award KPI points to serving staff
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
        cls,
        db: AsyncSession,
        appointment_id: int,
        student_id: int
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
        """O'tib ketgan sanalardagi kelinmagan (BOOKED) navbatlarni NO_SHOW holatiga o'tkazish."""
        tashkent_tz = timezone(timedelta(hours=5))
        now_local = datetime.now(tashkent_tz)
        today_str = now_local.strftime("%Y-%m-%d")

        stmt = select(Appointment).where(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.appointment_date < today_str
        )
        expired_appointments = (await db.execute(stmt)).scalars().all()
        count = len(expired_appointments)
        for app in expired_appointments:
            app.status = AppointmentStatus.NO_SHOW
            app.notes = (app.notes or "") + " [Avto-yopildi: Talaba belgilangan kunda kelmadi (No-Show)]"

        if count > 0:
            await db.commit()
        return count

