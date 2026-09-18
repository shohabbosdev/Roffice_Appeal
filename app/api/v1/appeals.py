from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import Appeal, AppealStatus, User, UserRole, Service
from app.schemas import (
    AppealCreate, AppealAssign, AppealReassign, AppealClarify,
    AppealProvideClarify, AppealResolve, AppealConfirm, AppealDispute,
    AppealEscalateProrektor, ProrektorFinalDecision, AppealOut,
    EducationFormPolicyOut, EducationFormPolicyUpdate
)
import asyncio
from app.services.appeal_service import AppealService
from app.services.policy_service import PolicyService
from app.services.telegram_service import TelegramService
from app.services.kpi_service import KPIService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/appeals", tags=["Murojaatlar (Online murojaat jarayoni)"])
logger = logging.getLogger(__name__)


def _appeal_options():
    return (
        selectinload(Appeal.service).selectinload(Service.department),
        selectinload(Appeal.student),
        selectinload(Appeal.assigned_staff)
    )


@router.get("/policy/education-forms", response_model=EducationFormPolicyOut, summary="Ta'lim shakllari onlayn murojaat cheklovlari siyosati")
async def get_education_form_policy(
    db: AsyncSession = Depends(get_db)
):
    """Barcha ta'lim shakllari bo'yicha joriy cheklov va ruxsatlar holatini olish."""
    return await PolicyService.get_education_form_policy(db)


@router.post("/policy/education-forms", response_model=EducationFormPolicyOut, summary="Ta'lim shakllari onlayn murojaat cheklovlarini o'zgartirish")
async def update_education_form_policy(
    data: EducationFormPolicyUpdate,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """Boshliq yoki admin tomonidan qaysi ta'lim shakllari onlayn murojaat yo'llashi mumkinligini belgilash."""
    return await PolicyService.update_education_form_policy(db, data.allowed_forms)


@router.post("", response_model=AppealOut, status_code=status.HTTP_201_CREATED, summary="Talaba tomonidan yangi murojaat yo'llash")
async def create_appeal(
    data: AppealCreate,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba o'z profilidan turib xizmat turi bo'yicha murojaat yaratadi."""
    # Ta'lim shakli tekshiruvi: faol siyosat bo'yicha ruxsat etilgan ta'lim shakllarini tekshirish
    allowed_forms = await PolicyService.get_allowed_education_forms(db)
    edu_form = (current_user.education_form or "").strip().lower()
    if not any(f in edu_form for f in allowed_forms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Onlayn murojaat yo'llash faqat sirtqi va masofaviy ta'lim shakli talabalari uchun mo'ljallangan "
                f"(sizning ta'lim shaklingiz: {current_user.education_form or 'kunduzgi'}). "
                "Kunduzgi ta'lim shakli talabalari Registrator ofisiga (104-xona) bevosita kelib murojaat qilishlari "
                "yoki 'Kelib hal etish' bo'limi orqali navbat band qilishlari mumkin."
            )
        )

    appeal = await AppealService.create_appeal(
        db=db,
        student_id=current_user.id,
        service_id=data.service_id,
        subject=data.subject,
        message=data.message,
        attachment_urls=data.attachment_urls
    )
    # Reload with service
    result = await db.execute(
        select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id)
    )
    reloaded_appeal = result.scalar_one()

    # Telegram orqali xabar jo'natish
    if current_user.telegram_chat_id:
        asyncio.create_task(TelegramService.notify_appeal_created(
            chat_id=current_user.telegram_chat_id,
            appeal_ticket=reloaded_appeal.ticket_number,
            subject=reloaded_appeal.subject,
            service_title=reloaded_appeal.service.title if reloaded_appeal.service else "-",
            deadline=reloaded_appeal.sla_deadline_at
        ))

    return reloaded_appeal


@router.get("", response_model=List[AppealOut], summary="Murojaatlar ro'yxatini olish (rolga mos filtrlangan)")
async def get_appeals(
    appeal_status: Optional[AppealStatus] = Query(None, description="Murojaat holati bo'yicha filter"),
    service_id: Optional[int] = Query(None, description="Xizmat ID bo'yicha filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Foydalanuvchi roliga qarab murojaatlar ro'yxati:
    - Talaba: faqat o'zining murojaatlarini ko'radi
    - Xodim: o'ziga biriktirilgan murojaatlarni ko'radi
    - Rahbariyat (Boshliq, Prorektor, Admin): barcha murojaatlarni ko'radi
    """
    query = select(Appeal).options(*_appeal_options())

    if current_user.role == UserRole.STUDENT:
        query = query.where(Appeal.student_id == current_user.id)
    elif current_user.role in [UserRole.FRONT_STAFF, UserRole.BACK_STAFF]:
        if current_user.department_id:
            query = query.join(Appeal.service).where(
                (Appeal.assigned_staff_id == current_user.id) |
                ((Appeal.status == AppealStatus.NEW) & (Appeal.assigned_staff_id.is_(None)) & (Service.department_id == current_user.department_id))
            )
        else:
            query = query.where(
                (Appeal.assigned_staff_id == current_user.id) |
                ((Appeal.status == AppealStatus.NEW) & (Appeal.assigned_staff_id.is_(None)))
            )

    if appeal_status:
        query = query.where(Appeal.status == appeal_status)
    if service_id:
        query = query.where(Appeal.service_id == service_id)

    query = query.order_by(Appeal.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{appeal_id}", response_model=AppealOut, summary="Murojaatning to'liq holati va tarixi")
async def get_appeal_detail(
    appeal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Murojaat tafsilotlari, ijro muddati va QR kod tekshiruvi."""
    result = await db.execute(
        select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Murojaat topilmadi.")

    # Access check: Student can only view own appeal
    if current_user.role == UserRole.STUDENT and appeal.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Siz faqat o'zingizning murojaatingizni ko'ra olasiz.")

    return appeal


@router.post("/{appeal_id}/assign", response_model=AppealOut, summary="Murojaatni ijrochiga biriktirish (Boshliq / Admin)")
async def assign_appeal(
    appeal_id: int,
    data: AppealAssign,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Registrator ofisi boshlig'i murojaatni tegishli Front yoki Back xodimga yo'naltiradi."""
    appeal = await AppealService.assign_appeal(
        db=db,
        appeal_id=appeal_id,
        staff_id=data.staff_id,
        assigned_by_user_id=current_user.id
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    reloaded_assigned = result.scalar_one()

    # Xodimga Telegram orqali xabar
    staff_user = await db.get(User, data.staff_id)
    student_user = await db.get(User, reloaded_assigned.student_id)
    if staff_user and staff_user.telegram_chat_id:
        asyncio.create_task(TelegramService.notify_appeal_assigned(
            staff_chat_id=staff_user.telegram_chat_id,
            appeal_ticket=reloaded_assigned.ticket_number,
            subject=reloaded_assigned.subject,
            student_name=student_user.full_name if student_user else "-",
            deadline=reloaded_assigned.sla_deadline_at
        ))

    return reloaded_assigned


@router.post("/{appeal_id}/reassign", response_model=AppealOut, summary="Murojaatni boshqa ijrochiga qayta yo'naltirish (Ping-pong nazorati)")
async def reassign_appeal(
    appeal_id: int,
    data: AppealReassign,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim vakolatiga kirmasa boshqasiga o'tkazadi. 1 martadan oshsa to'g'ridan-to'g'ri Boshliqqa qulflanadi."""
    appeal = await AppealService.reassign_appeal(
        db=db,
        appeal_id=appeal_id,
        new_staff_id=data.new_staff_id,
        current_staff_id=current_user.id,
        reason=data.reason
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/request-clarification", response_model=AppealOut, summary="Talabadan qo'shimcha ma'lumot so'rash (Timer to'xtatiladi)")
async def request_clarification(
    appeal_id: int,
    data: AppealClarify,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim ma'lumot yetarli bo'lmaganda talabaga savol yo'llaydi, SLA taymeri to'xtatiladi."""
    appeal = await AppealService.request_clarification(
        db=db,
        appeal_id=appeal_id,
        staff_id=current_user.id,
        clarification_message=data.clarification_message
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/provide-clarification", response_model=AppealOut, summary="Talaba tomonidan so'ralgan ma'lumotni kiritish")
async def provide_clarification(
    appeal_id: int,
    data: AppealProvideClarify,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba so'ralgan tushuntirishni yuboradi, ijro taymeri qayta tiklanadi."""
    existing = await db.get(Appeal, appeal_id)
    if not existing or existing.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Siz faqat o'z murojaatingizga ma'lumot qo'sha olasiz.")

    appeal = await AppealService.provide_clarification(
        db=db,
        appeal_id=appeal_id,
        student_id=current_user.id,
        additional_info=data.additional_info
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/resolve", response_model=AppealOut, summary="Murojaatni ijro etish va natijani yuklash (72 soatlik tasdiqlash boshlanadi)")
async def resolve_appeal(
    appeal_id: int,
    data: AppealResolve,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Ijrochi murojaatga javob yoki fayl yuklaydi. Natija QR kod bilan himoyalanadi."""
    appeal = await AppealService.resolve_appeal(
        db=db,
        appeal_id=appeal_id,
        staff_id=current_user.id,
        resolution_text=data.resolution_text,
        result_file_url=data.result_file_url
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    reloaded_resolved = result.scalar_one()

    # Talabaga Telegram orqali rasmiy javobni yetkazish
    student_user = await db.get(User, reloaded_resolved.student_id)
    if student_user and student_user.telegram_chat_id:
        asyncio.create_task(TelegramService.notify_appeal_resolved(
            student_chat_id=student_user.telegram_chat_id,
            appeal_ticket=reloaded_resolved.ticket_number,
            subject=reloaded_resolved.subject,
            resolution_text=reloaded_resolved.resolution_text or "Rasmiy javob tayyorlandi."
        ))

    return reloaded_resolved


@router.post("/{appeal_id}/confirm", response_model=AppealOut, summary="Talaba tomonidan ijroni tasdiqlash va baholash (1-5)")
async def confirm_resolution(
    appeal_id: int,
    data: AppealConfirm,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba natijadan qanoatlanganligini tasdiqlaydi. Baho xodimning KPI balliga ta'sir qiladi."""
    existing = await db.get(Appeal, appeal_id)
    if not existing or existing.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faqat murojaat egasi ijroni tasdiqlashi mumkin.")

    appeal = await AppealService.confirm_resolution(
        db=db,
        appeal_id=appeal_id,
        student_id=current_user.id,
        rating=data.rating,
        rating_comment=data.rating_comment
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/dispute", response_model=AppealOut, summary="Talaba tomonidan e'tiroz bildirish (Boshliqqa to'g'ridan-to'g'ri eskalatsiya)")
async def dispute_resolution(
    appeal_id: int,
    data: AppealDispute,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba 'Hal bo'lmadi' tugmasini bosadi. Murojaat xodimga qaytmaydi, to'g'ri Registrator ofisi boshlig'iga o'tadi."""
    existing = await db.get(Appeal, appeal_id)
    if not existing or existing.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faqat murojaat egasi e'tiroz bildirishi mumkin.")

    appeal = await AppealService.dispute_resolution(
        db=db,
        appeal_id=appeal_id,
        student_id=current_user.id,
        dispute_reason=data.dispute_reason
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/escalate-prorektor", response_model=AppealOut, summary="Nizoni Prorektorga yo'naltirishi (3-bosqich eskalatsiya)")
async def escalate_prorektor(
    appeal_id: int,
    data: AppealEscalateProrektor,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Ofis boshlig'i murakkab yoki yechilmagan nizoli murojaatni Prorektorga uzatadi."""
    appeal = await AppealService.escalate_to_prorektor(
        db=db,
        appeal_id=appeal_id,
        head_user_id=current_user.id,
        head_note=data.head_note
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()


@router.post("/{appeal_id}/prorektor-decision", response_model=AppealOut, summary="Prorektorning yakuniy majburiy qarori")
async def prorektor_decision(
    appeal_id: int,
    data: ProrektorFinalDecision,
    current_user: User = Depends(require_role(UserRole.VICE_RECTOR, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """O'quv ishlari bo'yicha prorektor yakuniy qaror chiqaradi va murojaatni yopadi."""
    appeal = await AppealService.prorektor_final_resolution(
        db=db,
        appeal_id=appeal_id,
        prorektor_user_id=current_user.id,
        final_decision=data.final_decision
    )
    result = await db.execute(select(Appeal).options(*_appeal_options()).where(Appeal.id == appeal.id))
    return result.scalar_one()
