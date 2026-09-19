from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import Appointment, AppointmentStatus, User, UserRole
from app.schemas import AppointmentBook, AppointmentComplete, AppointmentOut
import asyncio
from app.services.queue_service import QueueService
from app.services.telegram_service import TelegramService
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/appointments", tags=["Elektron navbat (Kelib / Uchrashib hal etish)"])


@router.get("/available-slots", summary="Belgilangan sana uchun bo'sh 15 daqiqalik vaqt oraliqlari yoki to'liq slotlar holati")
async def get_available_slots(
    appointment_date: str = Query(..., description="Sana formati: YYYY-MM-DD"),
    service_id: int = Query(..., description="Xizmat turi ID"),
    detailed: bool = Query(False, description="To'liq slot holatlari (o'tib ketgan, bloklangan, band) bilan olish"),
    db: AsyncSession = Depends(get_db)
):
    """Tanlangan xizmat va sana bo'yicha bo'sh yoki batafsil slot holatlarini qaytaradi."""
    if detailed:
        return await QueueService.get_detailed_slots(
            db=db,
            appointment_date=appointment_date,
            service_id=service_id
        )
    return await QueueService.get_available_slots(
        db=db,
        appointment_date=appointment_date,
        service_id=service_id
    )


@router.post("/book", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED, summary="Talaba tomonidan kelib hal etish uchun navbat olish")
async def book_appointment(
    data: AppointmentBook,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba o'ziga qulay 15 daqiqalik vaqtni tanlaydi va elektron talon oladi."""
    appointment = await QueueService.book_appointment(
        db=db,
        student_id=current_user.id,
        service_id=data.service_id,
        appointment_date=data.appointment_date,
        time_slot=data.time_slot
    )
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.id == appointment.id)
    )
    reloaded_appointment = result.scalar_one()

    # Talabaga Telegram orqali talon ma'lumotlarini yetkazish
    if current_user.telegram_chat_id:
        asyncio.create_task(TelegramService.notify_appointment_booked(
            student_chat_id=current_user.telegram_chat_id,
            ticket_code=reloaded_appointment.ticket_code,
            window_number=reloaded_appointment.window_number,
            appointment_date=reloaded_appointment.appointment_date,
            time_slot=reloaded_appointment.time_slot,
            service_title=reloaded_appointment.service.title if reloaded_appointment.service else "-"
        ))

    return reloaded_appointment


@router.get("", response_model=List[AppointmentOut], summary="Navbatlar ro'yxati (rolga qarab filtrlangan)")
async def get_appointments(
    appointment_date: Optional[str] = Query(None, description="Sana bo'yicha filter (YYYY-MM-DD)"),
    status_filter: Optional[AppointmentStatus] = Query(None, description="Navbat holati"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Foydalanuvchi roliga mos navbatlar ro'yxati."""
    query = select(Appointment).options(
        selectinload(Appointment.service),
        selectinload(Appointment.student)
    )

    if current_user.role == UserRole.STUDENT:
        query = query.where(Appointment.student_id == current_user.id)
    elif current_user.role in [UserRole.FRONT_STAFF, UserRole.BACK_STAFF]:
        query = query.where(
            (Appointment.staff_id == current_user.id) |
            (Appointment.staff_id.is_(None))
        )

    if appointment_date:
        query = query.where(Appointment.appointment_date == appointment_date)
    if status_filter:
        query = query.where(Appointment.status == status_filter)

    query = query.order_by(Appointment.appointment_date.desc(), Appointment.time_slot)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/today", response_model=List[AppointmentOut], summary="Bugungi kunga olingan navbatlar")
async def get_today_appointments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bugungi kun bo'yicha barcha faol navbatlar (live badge va monitoring uchun)."""
    now = QueueService.get_now()
    today_str = now.strftime("%Y-%m-%d")
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.appointment_date == today_str)
        .order_by(Appointment.scheduled_start.asc(), Appointment.id.asc())
    )
    return result.scalars().all()


@router.get("/my", response_model=List[AppointmentOut], summary="Talabaning barcha olingan navbat talonlari")
async def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Joriy talabaning barcha olingan talonlari ro'yxati."""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.student_id == current_user.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc())
    )
    return result.scalars().all()


@router.get("/live-board", summary="Kutish zali monitori (TV Display) uchun jonli navbat ma'lumotlari")
async def get_live_queue_board(
    db: AsyncSession = Depends(get_db)
):
    """
    Kutish zali katta ekrani uchun real-vaqtdagi navbat ma'lumotlari:
    oxirgi chaqirilgan talon, darchalar bo'yicha faol xizmatlar, kutayotganlar ro'yxati va statistika.
    (Ommaviy, avtorizatsiyasiz).
    """
    return await QueueService.get_live_board_data(db=db)


@router.get("/{appointment_id}", response_model=AppointmentOut, summary="Navbat taloni tafsilotlari")
async def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Talon ma'lumotlari, darcha raqami va belgilangan vaqt."""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Navbat topilmadi.")

    if current_user.role == UserRole.STUDENT and appointment.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Siz faqat o'z navbatingizni ko'ra olasiz.")

    return appointment


@router.post("/{appointment_id}/check-in", response_model=AppointmentOut, summary="Talabaning ofisga kelganini tasdiqlash (Check-in)")
async def check_in_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Talaba ofisga kelib terminalda talonini tasdiqlaydi."""
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Navbat topilmadi.")

    # Access control: Student can only check-in own ticket; Staff can check-in any ticket
    if current_user.role == UserRole.STUDENT and appointment.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz faqat o'zingizning navbat taloningizni tasdiqlay olasiz."
        )

    appointment.status = AppointmentStatus.CHECKED_IN
    await db.commit()
    await db.refresh(appointment)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.id == appointment.id)
    )
    return result.scalar_one()


@router.post("/{appointment_id}/call", response_model=AppointmentOut, summary="Talabani darchaga chaqirish")
async def call_appointment(
    appointment_id: int,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim navbatdagi talabani o'z darchasiga chaqiradi. Holat 'in_service' ga o'tadi va jonli tabloga yuboriladi."""
    appointment = await QueueService.call_appointment(
        db=db,
        appointment_id=appointment_id,
        staff=current_user
    )

    # Talabaning Telegramiga darhol "Darchaga marhamat" bildirishnomasi
    if appointment.student and appointment.student.telegram_chat_id:
        asyncio.create_task(TelegramService.notify_appointment_called(
            student_chat_id=appointment.student.telegram_chat_id,
            ticket_code=appointment.ticket_code,
            window_number=appointment.window_number
        ))

    await AuditService.log(
        db=db,
        entity_type="appointment",
        entity_id=appointment.id,
        action="appointment_called",
        user_id=current_user.id,
        details=f"Talon chaqirildi: {appointment.ticket_code} (Darcha: {appointment.window_number})"
    )

    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentOut, summary="Qabulni yakunlash va xodimga KPI ballini yozish")
async def complete_appointment(
    appointment_id: int,
    data: AppointmentComplete,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim talaba bilan muloqotni yakunlaydi va tizim xodimga xizmatning KPI ballini hisoblaydi."""
    appointment = await QueueService.complete_appointment(
        db=db,
        appointment_id=appointment_id,
        staff_id=current_user.id,
        notes=data.notes
    )
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.id == appointment.id)
    )
    reloaded_appointment = result.scalar_one()

    await AuditService.log(
        db=db,
        entity_type="appointment",
        entity_id=reloaded_appointment.id,
        action="appointment_completed",
        user_id=current_user.id,
        details=f"Qabul yakunlandi: {reloaded_appointment.ticket_code}"
    )

    return reloaded_appointment


@router.delete("/{appointment_id}", response_model=AppointmentOut, summary="Navbatni bekor qilish (DELETE)")
@router.post("/{appointment_id}/cancel", response_model=AppointmentOut, summary="Navbatni bekor qilish (POST)")
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Talaba yoki xodim tomonidan navbat bekor qilinadi."""
    if current_user.role == UserRole.STUDENT:
        appointment = await QueueService.cancel_appointment(
            db=db,
            appointment_id=appointment_id,
            student_id=current_user.id
        )
    else:
        appointment = await db.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Navbat topilmadi.")
        appointment.status = AppointmentStatus.CANCELLED
        await db.commit()
        await db.refresh(appointment)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.student))
        .where(Appointment.id == appointment.id)
    )
    return result.scalar_one()
