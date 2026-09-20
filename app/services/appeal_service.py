import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Appeal, AppealStatus, Service, User, UserRole, AuditLog, Appointment, AppointmentStatus
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
        await db.flush()

        # Audit log
        log = AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=appeal.id,
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
        appeal.qr_hash = qr_hash

        # Agar natija fayli xodim tomonidan yuklanmagan bo'lsa, rasmiy QR-kodli PDF generatsiya qilish
        if not result_file_url:
            student = await db.get(User, appeal.student_id)
            staff = await db.get(User, staff_id) if staff_id else None
            service = await db.get(Service, appeal.service_id)
            if student:
                try:
                    from app.services.document_generator import DocumentGenerator
                    is_ref = "ma'lumotnoma" in (service.title.lower() if service else "") or "malumotnoma" in (service.code.lower() if service else "")
                    if is_ref:
                        result_file_url = DocumentGenerator.generate_student_reference_pdf(
                            student=student,
                            qr_hash=qr_hash,
                            ticket_number=appeal.ticket_number
                        )
                    else:
                        result_file_url = DocumentGenerator.generate_appeal_resolution_pdf(
                            appeal=appeal,
                            student=student,
                            staff=staff,
                            qr_hash=qr_hash
                        )
                except Exception as e:
                    # PDF generatsiyasida xatolik bo'lsa ham ijro to'xtab qolmasligi uchun
                    pass

        appeal.result_file_url = result_file_url
        appeal.confirmation_deadline_at = now + timedelta(hours=settings.CONFIRMATION_TIMEOUT_HOURS)

        db.add(AuditLog(
            user_id=staff_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="resolved",
            details=f"Xodim javob berdi. Rasmiy elektron PDF va QR yaratildi (QR: {qr_hash})"
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
            # Xodim mehnati uchun kpi_points beriladi, biroq talaba baholamaganligi sababli sun'iy 5 baho qo'shilmaydi (rating=None)
            if app.assigned_staff_id:
                await KPIService.record_completed_service(
                    db=db,
                    employee_id=app.assigned_staff_id,
                    kpi_points=app.earned_kpi_points,
                    rating=None,
                    is_appointment=False
                )
            count += 1

        if count > 0:
            await db.commit()
        return count

    @classmethod
    async def get_executive_analytics(
        cls, db: AsyncSession, period_filter: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """Rahbariyat (Ofis boshlig'i, Prorektor, Admin) uchun umumiy tahliliy ko'rsatkichlar."""
        now = datetime.now(timezone.utc)

        # 1. Sana bo'yicha filter
        stmt = (
            select(Appeal)
            .options(
                selectinload(Appeal.service),
                selectinload(Appeal.student),
                selectinload(Appeal.assigned_staff)
            )
            .order_by(Appeal.created_at.asc())
        )

        if period_filter == "this_month":
            start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(Appeal.created_at >= start_month)
        elif period_filter == "last_30_days":
            start_date = now - timedelta(days=30)
            stmt = stmt.where(Appeal.created_at >= start_date)
        elif period_filter == "this_year":
            start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(Appeal.created_at >= start_year)

        result = await db.execute(stmt)
        appeals = result.scalars().all()

        total_appeals = len(appeals)

        # 2. Status hisoblagichlari
        status_counts = defaultdict(int)
        for a in appeals:
            status_counts[a.status.value] += 1

        completed_appeals = status_counts["resolved"] + status_counts["completed"] + status_counts["auto_closed"]
        in_progress_appeals = (
            status_counts["new"] + status_counts["assigned"] + status_counts["in_progress"] +
            status_counts["clarification_needed"] + status_counts["pending_external"]
        )
        rejected_appeals = status_counts["rejected"]
        disputed_appeals = (
            status_counts["disputed"] + status_counts["escalated_head"] + status_counts["escalated_prorektor"]
        )

        # 3. SLA compliance (O'z vaqtida bajarilish ko'rsatkichi) va O'rtacha yopilish vaqti
        resolved_appeals = [a for a in appeals if a.resolved_at and a.status in [AppealStatus.RESOLVED, AppealStatus.COMPLETED, AppealStatus.AUTO_CLOSED]]
        on_time_count = 0
        total_resolution_seconds = 0.0

        for a in resolved_appeals:
            if a.sla_deadline_at and a.resolved_at <= a.sla_deadline_at:
                on_time_count += 1
            if a.resolved_at and a.created_at:
                total_resolution_seconds += max(0, (a.resolved_at - a.created_at).total_seconds())

        sla_compliance_percent = round((on_time_count / len(resolved_appeals) * 100), 1) if resolved_appeals else 100.0
        avg_resolution_hours = round((total_resolution_seconds / len(resolved_appeals) / 3600), 1) if resolved_appeals else 0.0

        # 4. Talabalar qoniqish reytingi
        rated_appeals = [a.rating for a in appeals if a.rating is not None]
        avg_student_rating = round(sum(rated_appeals) / len(rated_appeals), 2) if rated_appeals else 5.0

        # 5. Fakultetlar kesimida tahlil
        faculty_data = defaultdict(lambda: {"total": 0, "completed": 0, "disputed": 0, "ratings": []})
        for a in appeals:
            fac = (a.student.faculty if a.student and a.student.faculty else "Umumiy / Belgilanmagan").strip()
            faculty_data[fac]["total"] += 1
            if a.status in [AppealStatus.RESOLVED, AppealStatus.COMPLETED, AppealStatus.AUTO_CLOSED]:
                faculty_data[fac]["completed"] += 1
            if a.status in [AppealStatus.DISPUTED, AppealStatus.ESCALATED_HEAD, AppealStatus.ESCALATED_PROREKTOR]:
                faculty_data[fac]["disputed"] += 1
            if a.rating is not None:
                faculty_data[fac]["ratings"].append(a.rating)

        by_faculty = []
        for fac_name, stat in faculty_data.items():
            avg_r = round(sum(stat["ratings"]) / len(stat["ratings"]), 1) if stat["ratings"] else 5.0
            by_faculty.append({
                "faculty": fac_name,
                "total": stat["total"],
                "completed": stat["completed"],
                "disputed": stat["disputed"],
                "avg_rating": avg_r
            })
        by_faculty.sort(key=lambda x: x["total"], reverse=True)

        # 6. Top-5 talabgir xizmatlar
        service_counts = defaultdict(lambda: {"count": 0, "service_id": None, "code": ""})
        for a in appeals:
            stitle = a.service.title if a.service else "Boshqa xizmatlar"
            service_counts[stitle]["count"] += 1
            if a.service:
                service_counts[stitle]["service_id"] = a.service.id
                service_counts[stitle]["code"] = a.service.code

        top_services = []
        for stitle, item in service_counts.items():
            pct = round(item["count"] / total_appeals * 100, 1) if total_appeals > 0 else 0.0
            top_services.append({
                "service_id": item["service_id"],
                "code": item["code"],
                "title": stitle,
                "count": item["count"],
                "percentage": pct
            })
        top_services.sort(key=lambda x: x["count"], reverse=True)
        top_services = top_services[:5]

        # 7. Dinamika trendi (Oxirgi 14 kunlik kunlik tushum va ijro)
        days_map = {}
        for i in range(13, -1, -1):
            d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            days_map[d_str] = {"date": d_str, "total": 0, "completed": 0}

        for a in appeals:
            c_date = a.created_at.strftime("%Y-%m-%d")
            if c_date in days_map:
                days_map[c_date]["total"] += 1
            if a.resolved_at:
                r_date = a.resolved_at.strftime("%Y-%m-%d")
                if r_date in days_map:
                    days_map[r_date]["completed"] += 1

        trends = list(days_map.values())

        # 8. Jami qabul navbatlari soni
        appt_count_stmt = select(func.count(Appointment.id))
        total_appointments = (await db.execute(appt_count_stmt)).scalar() or 0

        return {
            "period": period_filter,
            "generated_at": now.isoformat(),
            "summary": {
                "total_appeals": total_appeals,
                "completed_appeals": completed_appeals,
                "in_progress_appeals": in_progress_appeals,
                "rejected_appeals": rejected_appeals,
                "disputed_appeals": disputed_appeals,
                "sla_compliance_percent": sla_compliance_percent,
                "avg_resolution_hours": avg_resolution_hours,
                "avg_student_rating": avg_student_rating,
                "total_appointments": total_appointments
            },
            "by_faculty": by_faculty,
            "top_services": top_services,
            "by_status": dict(status_counts),
            "trends": trends
        }

    @classmethod
    async def get_live_badges_summary(
        cls, db: AsyncSession, current_user: User
    ) -> Dict[str, Any]:
        """Xodimlar uchun yengil va tezkor real-vaqt bildirishnomalari hisoblagichi."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        urgent_threshold = now + timedelta(hours=2)

        # 1. Yangi arizalar (status == new)
        new_stmt = select(func.count(Appeal.id)).where(Appeal.status == AppealStatus.NEW)
        new_appeals = (await db.execute(new_stmt)).scalar() or 0

        # 2. Xodimning o'ziga biriktirilgan faol arizalari
        my_stmt = select(func.count(Appeal.id)).where(
            Appeal.assigned_staff_id == current_user.id,
            Appeal.status.in_([
                AppealStatus.ASSIGNED,
                AppealStatus.IN_PROGRESS,
                AppealStatus.CLARIFICATION_NEEDED,
                AppealStatus.PENDING_EXTERNAL
            ])
        )
        my_assigned = (await db.execute(my_stmt)).scalar() or 0

        # 3. Nizoli / Rahbariyatga oshirilgan arizalar
        dispute_stmt = select(func.count(Appeal.id)).where(
            Appeal.status.in_([
                AppealStatus.DISPUTED,
                AppealStatus.ESCALATED_HEAD,
                AppealStatus.ESCALATED_PROREKTOR
            ])
        )
        disputed_appeals = (await db.execute(dispute_stmt)).scalar() or 0

        # 4. SLA muddati tugashiga 2 soat qolgan shoshilinch arizalar
        open_statuses = [
            AppealStatus.NEW,
            AppealStatus.ASSIGNED,
            AppealStatus.IN_PROGRESS,
            AppealStatus.CLARIFICATION_NEEDED,
            AppealStatus.PENDING_EXTERNAL,
            AppealStatus.DISPUTED,
            AppealStatus.ESCALATED_HEAD,
            AppealStatus.ESCALATED_PROREKTOR
        ]
        urgent_stmt = select(func.count(Appeal.id)).where(
            Appeal.status.in_(open_statuses),
            Appeal.sla_deadline_at.isnot(None),
            Appeal.sla_deadline_at >= now,
            Appeal.sla_deadline_at <= urgent_threshold
        )
        if current_user.role == UserRole.BACK_STAFF:
            urgent_stmt = urgent_stmt.where(Appeal.assigned_staff_id == current_user.id)
        urgent_sla_appeals = (await db.execute(urgent_stmt)).scalar() or 0

        # 5. Bugungi darcha navbatida kutayotganlar
        queue_stmt = select(func.count(Appointment.id)).where(
            Appointment.appointment_date == today_str,
            Appointment.status.in_([
                AppointmentStatus.BOOKED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_SERVICE
            ])
        )
        today_waiting_appointments = (await db.execute(queue_stmt)).scalar() or 0

        # 6. Oxirgi ariza ID si va yaratilgan vaqti
        last_appeal_stmt = select(Appeal.id, Appeal.created_at).order_by(Appeal.id.desc()).limit(1)
        last_res = (await db.execute(last_appeal_stmt)).first()
        last_appeal_id = last_res[0] if last_res else 0
        last_appeal_created_at = last_res[1].isoformat() if last_res and last_res[1] else None

        return {
            "new_appeals": new_appeals,
            "my_assigned": my_assigned,
            "disputed_appeals": disputed_appeals,
            "urgent_sla_appeals": urgent_sla_appeals,
            "today_waiting_appointments": today_waiting_appointments,
            "last_appeal_id": last_appeal_id,
            "last_appeal_created_at": last_appeal_created_at,
            "server_time": now.isoformat()
        }

    @classmethod
    async def cancel_appeal_by_student(
        cls, db: AsyncSession, appeal_id: int, student_id: int, reason: Optional[str] = None
    ) -> Appeal:
        """Talaba o'z arizasi hali xodim tomonidan ko'rib chiqishga olinmagan (NEW) paytda uni bekor qilishi."""
        appeal = await db.get(Appeal, appeal_id)
        if not appeal:
            raise HTTPException(status_code=404, detail="Murojaat topilmadi.")

        if appeal.student_id != student_id:
            raise HTTPException(status_code=403, detail="Siz faqat o'zingiz yaratgan murojaatni bekor qila olasiz.")

        if appeal.status != AppealStatus.NEW:
            raise HTTPException(
                status_code=400,
                detail=f"Ushbu murojaatni bekor qilib bo'lmaydi. U mas'ul xodim tomonidan ijroga qabul qilingan (holati: {appeal.status.value})."
            )

        appeal.status = AppealStatus.CANCELLED
        clean_reason = reason or "Talaba tomonidan sabab ko'rsatilmadi"
        appeal.resolution_text = f"[Talaba tomonidan bekor qilindi]: {clean_reason}"
        appeal.dispute_reason = f"[Talaba tomonidan bekor qilindi]: {clean_reason}"

        log = AuditLog(
            user_id=student_id,
            entity_type="appeal",
            entity_id=appeal.id,
            action="cancelled_by_student",
            details=f"Talaba o'z arizasini bekor qildi. Sabab: {clean_reason}"
        )
        db.add(log)
        await db.commit()
        await db.refresh(appeal)
        return appeal

