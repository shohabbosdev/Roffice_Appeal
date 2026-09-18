import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Appeal, AppealStatus, Service, User, UserRole, AuditLog
from app.services.sla_service import SLAService
from app.services.kpi_service import KPIService
from app.core.config import settings


class AppealService:
    @classmethod
    async def create_appeal(
        cls,
        db: AsyncSession,
        student_id: int,
        service_id: int,
        subject: str,
        message: str,
        attachment_urls: Optional[str] = None
    ) -> Appeal:
        """Create new student appeal with SLA deadline and Anti-Spam check."""
        # 1. Anti-Spam / Anti-Flood: Check if open appeal for same service exists
        stmt = select(Appeal).where(
            Appeal.student_id == student_id,
            Appeal.service_id == service_id,
            Appeal.status.in_([
                AppealStatus.NEW, AppealStatus.ASSIGNED, AppealStatus.IN_PROGRESS,
                AppealStatus.CLARIFICATION_NEEDED, AppealStatus.PENDING_EXTERNAL,
                AppealStatus.RESOLVED, AppealStatus.DISPUTED
            ])
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Sizda ushbu xizmat bo'yicha ko'rib chiqilayotgan faol murojaat mavjud (#{existing.ticket_number})."
            )

        service = await db.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Xizmat topilmadi.")

        now = datetime.now(timezone.utc)
        sla_deadline = SLAService.calculate_deadline(now, service.sla_hours)
        ticket_number = f"APP-{now.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        appeal = Appeal(
            ticket_number=ticket_number,
            student_id=student_id,
            service_id=service_id,
            status=AppealStatus.NEW,
            subject=subject,
            message=message,
            attachment_urls=attachment_urls,
            created_at=now,
            sla_deadline_at=sla_deadline,
            earned_kpi_points=service.kpi_points
        )
        db.add(appeal)

        # Audit log
        log = AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=0,
            action="created",
            details=f"Yangi murojaat yaratildi (#{ticket_number}), SLA muddati: {sla_deadline.strftime('%Y-%m-%d %H:%M')}"
        )
        db.add(log)

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def assign_appeal(
        cls, db: AsyncSession, appeal_id: int, staff_id: int, assigned_by_user_id: int
    ) -> Appeal:
        """Office head routes appeal to front/back staff member."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        appeal.assigned_staff_id = staff_id
        appeal.assigned_at = datetime.now(timezone.utc)
        appeal.status = AppealStatus.ASSIGNED

        db.add(AuditLog(
            user_id=assigned_by_user_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="assigned",
            details=f"Xodimga biriktirildi (staff_id: {staff_id})"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def reassign_appeal(
        cls, db: AsyncSession, appeal_id: int, new_staff_id: int, current_staff_id: int, reason: str
    ) -> Appeal:
        """Internal reassign with Ping-Pong prevention (limit: 1 time)."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        if appeal.reassign_count >= 1:
            # Lock to Office Head as Internal Dispute
            appeal.status = AppealStatus.ESCALATED_HEAD
            appeal.assigned_staff_id = None
            db.add(AuditLog(
                user_id=current_staff_id,
                entity_type="appeal",
                entity_id=appeal.id,
                action="internal_dispute_locked",
                details=f"Qayta yo'naltirish limiti tugadi. Boshliqqa ichki nizo sifatida qulflab o'tkazildi: {reason}"
            ))
        else:
            appeal.reassign_count += 1
            appeal.assigned_staff_id = new_staff_id
            appeal.status = AppealStatus.ASSIGNED
            db.add(AuditLog(
                user_id=current_staff_id,
                entity_type="appeal",
                entity_id=appeal.id,
                action="reassigned",
                details=f"Boshqa xodimga o'tkazildi (sabab: {reason})"
            ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def request_clarification(
        cls, db: AsyncSession, appeal_id: int, staff_id: int, clarification_message: str
    ) -> Appeal:
        """Staff requests clarification; timer pauses."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        appeal.status = AppealStatus.CLARIFICATION_NEEDED
        appeal.clarification_message = clarification_message

        db.add(AuditLog(
            user_id=staff_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="clarification_requested",
            details=f"Talabaga tushuntirish so'rovi yuborildi: {clarification_message}"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def provide_clarification(
        cls, db: AsyncSession, appeal_id: int, student_id: int, additional_info: str
    ) -> Appeal:
        """Student responds to clarification; timer resumes."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        appeal.message += f"\n\n[Qo'shimcha ma'lumot]: {additional_info}"
        appeal.status = AppealStatus.IN_PROGRESS
        appeal.clarification_message = None

        db.add(AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="clarification_provided",
            details="Talaba so'ralgan ma'lumotni kiritdi, ijro qayta tiklandi."
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def resolve_appeal(
        cls,
        db: AsyncSession,
        appeal_id: int,
        staff_id: int,
        resolution_text: str,
        result_file_url: Optional[str] = None
    ) -> Appeal:
        """Staff marks appeal as resolved; activates 72-hour confirmation window."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        now = datetime.now(timezone.utc)
        qr_hash = uuid.uuid4().hex[:16].upper()

        appeal.status = AppealStatus.RESOLVED
        appeal.resolved_at = now
        appeal.resolution_text = resolution_text
        appeal.result_file_url = result_file_url
        appeal.qr_hash = qr_hash
        appeal.confirmation_deadline_at = now + timedelta(hours=settings.CONFIRMATION_TIMEOUT_HOURS)

        db.add(AuditLog(
            user_id=staff_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="resolved",
            details=f"Xodim javob berdi. 72 soatlik tasdiqlash muddati boshlandi (QR: {qr_hash})"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def confirm_resolution(
        cls,
        db: AsyncSession,
        appeal_id: int,
        student_id: int,
        rating: int,
        rating_comment: Optional[str] = None
    ) -> Appeal:
        """Student confirms resolution, rates 1-5, and awards KPI points to staff."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Baho 1 dan 5 gacha bo'lishi shart.")

        if rating <= 2 and not rating_comment:
            raise HTTPException(status_code=400, detail="Past baho (1 yoki 2) uchun majburiy izoh yozilishi shart.")

        now = datetime.now(timezone.utc)
        appeal.status = AppealStatus.COMPLETED
        appeal.closed_at = now
        appeal.rating = rating
        appeal.rating_comment = rating_comment

        # Award KPI points to assigned staff
        if appeal.assigned_staff_id:
            await KPIService.record_completed_service(
                db=db,
                employee_id=appeal.assigned_staff_id,
                kpi_points=appeal.earned_kpi_points,
                rating=rating,
                is_appointment=False
            )

        db.add(AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="completed",
            details=f"Talaba qanoatlandi deb tasdiqladi (Baho: {rating} yulduzcha)"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def dispute_resolution(
        cls, db: AsyncSession, appeal_id: int, student_id: int, dispute_reason: str
    ) -> Appeal:
        """Student disputes resolution; escalates directly to Office Head (never returns to staff!)."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        if not dispute_reason or len(dispute_reason.strip()) < 5:
            raise HTTPException(status_code=400, detail="E'tiroz sababi batafsil yozilishi shart.")

        appeal.status = AppealStatus.DISPUTED
        appeal.dispute_reason = dispute_reason

        db.add(AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="disputed",
            details=f"Talaba e'tiroz bildirdi. Boshliqqa eskalatsiya qilindi: {dispute_reason}"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def escalate_to_prorektor(
        cls, db: AsyncSession, appeal_id: int, head_user_id: int, head_note: str
    ) -> Appeal:
        """Office Head escalates unresolved dispute to Vice-Rector (Tier-3)."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        appeal.status = AppealStatus.ESCALATED_PROREKTOR
        db.add(AuditLog(
            user_id=head_user_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="escalated_prorektor",
            details=f"Boshliq tomonidan Prorektorga yo'naltirildi: {head_note}"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def prorektor_final_resolution(
        cls, db: AsyncSession, appeal_id: int, prorektor_user_id: int, final_decision: str
    ) -> Appeal:
        """Vice-Rector issues final binding decision and officially closes dispute."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        now = datetime.now(timezone.utc)
        appeal.status = AppealStatus.COMPLETED
        appeal.closed_at = now
        appeal.resolution_text = f"[Prorektorning yakuniy qarori]: {final_decision}"

        db.add(AuditLog(
            user_id=prorektor_user_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="final_resolution_closed",
            details=f"Prorektor yakuniy qaror chiqardi: {final_decision}"
        ))

        await db.commit()
        await db.refresh(appeal)
        return appeal

    @classmethod
    async def auto_close_expired(cls, db: AsyncSession) -> int:
        """Auto-close appeals where 72h passed without student confirmation."""
        now = datetime.now(timezone.utc)
        stmt = select(Appeal).where(
            Appeal.status == AppealStatus.RESOLVED,
            Appeal.confirmation_deadline_at <= now
        )
        result = await db.execute(stmt)
        appeals = result.scalars().all()

        count = 0
        for app in appeals:
            app.status = AppealStatus.AUTO_CLOSED
            app.closed_at = now
            # Award points to staff for auto-closed tickets with default rating
            if app.assigned_staff_id:
                await KPIService.record_completed_service(
                    db=db,
                    employee_id=app.assigned_staff_id,
                    kpi_points=app.earned_kpi_points,
                    rating=5,
                    is_appointment=False
                )
            count += 1

        if count > 0:
            await db.commit()
        return count
