from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models import Appeal, AppealStatus, User, Service, Department
from app.schemas import AppealTrackStep, AppealTrackInfoOut, AppealPublicTrackOut
from app.services.sla_service import SLAService


class AppealTrackerService:
    @staticmethod
    def _mask_student_name(full_name: Optional[str]) -> str:
        """Talaba shaxsiy ma'lumotlarini (PII) himoyalash: Shohabbos Fayzullayev -> S*** F***"""
        if not full_name:
            return "Talaba"
        parts = full_name.strip().split()
        masked_parts = []
        for p in parts:
            if len(p) > 1:
                masked_parts.append(p[0].upper() + "***")
            else:
                masked_parts.append(p.upper() + "***")
        return " ".join(masked_parts)

    @classmethod
    async def _get_queue_ahead_count(cls, db: AsyncSession, appeal: Appeal) -> int:
        """Agar xodimga biriktirilgan bo'lsa, ushbu xodimda shu arizadan oldin navbatda turgan faol arizalar soni."""
        if not appeal.assigned_staff_id or appeal.status in [AppealStatus.RESOLVED, AppealStatus.COMPLETED, AppealStatus.REJECTED]:
            return 0

        # O'sha xodimga topshirilgan va hali yopilmagan, shu arizadan oldinroq yaratilgan arizalar
        q = select(func.count(Appeal.id)).where(
            Appeal.assigned_staff_id == appeal.assigned_staff_id,
            Appeal.status.in_([AppealStatus.NEW, AppealStatus.ASSIGNED, AppealStatus.IN_PROGRESS]),
            Appeal.created_at < appeal.created_at
        )
        res = await db.execute(q)
        return res.scalar() or 0

    @classmethod
    def _get_estimated_completion(
        cls, appeal: Appeal, queue_ahead: int, now: datetime
    ) -> Tuple[str, bool, int]:
        """
        Dinamik taxminiy tayyor bo'lish vaqtini hisoblaydi.
        Qaytaradi: (estimated_text, is_working_hours, progress_percentage)
        """
        # Toshkent vaqti
        tz_tashkent = timezone(timedelta(hours=5))
        now_tashkent = now.astimezone(tz_tashkent)
        is_work_time = SLAService.is_working_time(now_tashkent)

        # Agar ariza yopilgan bo'lsa
        if appeal.status == AppealStatus.COMPLETED:
            return ("Murojaat to'liq yakunlangan va arxivlangan", is_work_time, 100)
        if appeal.status == AppealStatus.REJECTED:
            return ("Murojaat rad etilgan", is_work_time, 100)
        if appeal.status == AppealStatus.RESOLVED:
            return ("Xizmat ijrosi yakunlandi. Talaba tasdiqlashi kutilmoqda", is_work_time, 90)
        if appeal.status in [AppealStatus.DISPUTED, AppealStatus.ESCALATED_HEAD, AppealStatus.ESCALATED_PROREKTOR]:
            return ("Rahbariyat tomonidan maxsus ko'rib chiqilmoqda (24 soat ichida)", is_work_time, 75)

        # IN_PROGRESS yoki ASSIGNED holatida
        progress_pct = 55 if appeal.status in [AppealStatus.IN_PROGRESS, AppealStatus.ASSIGNED] else 25

        if not appeal.sla_deadline_at:
            if not is_work_time:
                return ("Hozir rasmiy ish vaqti emas. Ko'rib chiqish ertaga 09:00 da davom etadi", False, progress_pct)
            return ("Bugun ish kuni yakuniga qadar (taxminan 2-4 soat ichida)", True, progress_pct)

        deadline_tashkent = appeal.sla_deadline_at.astimezone(tz_tashkent)
        diff_seconds = (deadline_tashkent - now_tashkent).total_seconds()

        # Agar muddat o'tib ketgan bo'lsa
        if diff_seconds <= 0:
            return ("Ijro muddati nazoratga olingan. Kutilayotgan javob: 1 soat ichida", is_work_time, progress_pct)

        diff_hours = int(diff_seconds // 3600)
        diff_minutes = int((diff_seconds % 3600) // 60)

        # Navbatdagi o'rniga qarab tuzatish
        queue_note = f" (Sizdan oldin: {queue_ahead} ta ariza)" if queue_ahead > 0 else ""

        if diff_hours < 1:
            est_text = f"Taxminan {diff_minutes} daqiqa ichida tayyor bo'ladi{queue_note}"
        elif diff_hours < 5:
            est_text = f"Taxminan {diff_hours} soat {diff_minutes} daqiqa ichida ({deadline_tashkent.strftime('%H:%M')} gacha){queue_note}"
        else:
            days = diff_hours // 8 # 8 soatlik ish kuni hisobida
            if days >= 1:
                est_text = f"{deadline_tashkent.strftime('%d-%b %H:%M')} gacha (taxminan {days} ish kuni){queue_note}"
            else:
                est_text = f"Bugun {deadline_tashkent.strftime('%H:%M')} gacha{queue_note}"

        if not is_work_time:
            est_text += " [Hozir ish vaqti emas. Jarayon 09:00 da davom etadi]"

        return (est_text, is_work_time, progress_pct)

    @classmethod
    def _build_steps(cls, appeal: Appeal) -> List[AppealTrackStep]:
        """Arizaning barcha 5 bosqichini uning joriy holati va sanalari bilan tuzish."""
        steps: List[AppealTrackStep] = []

        # 1. SUBMITTED
        step1_status = "completed"
        step1_desc = f"Murojaat tizimda muvaffaqiyatli ro'yxatga olindi (#{appeal.ticket_number})"
        steps.append(AppealTrackStep(
            step_key="submitted",
            title="Murojaat qabul qilindi",
            description=step1_desc,
            status=step1_status,
            timestamp=appeal.created_at,
            actor_name="Talaba",
            actor_role="Murojaatchi",
            icon="document-check"
        ))

        # 2. IN_PROGRESS / ASSIGNED
        has_assigned = appeal.assigned_at is not None or appeal.status not in [AppealStatus.NEW]
        if appeal.status == AppealStatus.NEW:
            step2_status = "pending"
            step2_desc = "Mas'ul xodimga biriktirilishi kutilmoqda"
        elif appeal.status in [AppealStatus.IN_PROGRESS, AppealStatus.ASSIGNED]:
            step2_status = "current"
            staff_name = appeal.assigned_staff.full_name if appeal.assigned_staff else "Mas'ul xodim"
            step2_desc = f"{staff_name} tomonidan ko'rib chiqilmoqda va hujjatlar o'rganilmoqda"
        else:
            step2_status = "completed"
            staff_name = appeal.assigned_staff.full_name if appeal.assigned_staff else "Mas'ul xodim"
            step2_desc = f"{staff_name} tomonidan to'liq ko'rib chiqildi"

        steps.append(AppealTrackStep(
            step_key="assigned",
            title="Mas'ul xodim ko'rib chiqmoqda",
            description=step2_desc,
            status=step2_status,
            timestamp=appeal.assigned_at,
            actor_name=appeal.assigned_staff.full_name if appeal.assigned_staff else None,
            actor_role="Registrator ofisi mutaxassisi",
            icon="user-gear"
        ))

        # 3. Maxsus nazorat / Eskalatsiya (agar mavjud bo'lsa)
        is_disputed = appeal.status in [AppealStatus.DISPUTED, AppealStatus.ESCALATED_HEAD, AppealStatus.ESCALATED_PROREKTOR]
        if is_disputed or appeal.reassign_count > 0:
            if is_disputed:
                esc_status = "current"
                esc_title = "Rahbariyat nazorati (Nizo / Eskalatsiya)"
                d_reason = appeal.dispute_reason or "Qayta ko'rib chiqish so'ralgan"
                esc_desc = f"Talaba e'tirozi: '{d_reason}'. Rahbariyat tekshirmoqda."
            else:
                esc_status = "completed"
                esc_title = "Xizmat optimallashtirildi"
                esc_desc = f"Murojaat ixtisoslashgan xodimga qayta yo'naltirildi ({appeal.reassign_count} marta)."

            steps.append(AppealTrackStep(
                step_key="escalated",
                title=esc_title,
                description=esc_desc,
                status=esc_status,
                timestamp=appeal.resolved_at or appeal.assigned_at,
                actor_name="Filial Rahbariyati",
                actor_role="Nazorat sektori",
                icon="shield-alert"
            ))

        # 4. RESOLVED
        if appeal.status in [AppealStatus.NEW, AppealStatus.ASSIGNED, AppealStatus.IN_PROGRESS, AppealStatus.DISPUTED, AppealStatus.ESCALATED_HEAD, AppealStatus.ESCALATED_PROREKTOR]:
            step4_status = "pending"
            step4_desc = "Ijro xulosasi va rasmiy hujjat tayyorlanishi kutilmoqda"
        elif appeal.status == AppealStatus.RESOLVED:
            step4_status = "current"
            step4_desc = f"Xizmat ijrosi yakunlandi. {appeal.resolution_text or ''}"
        elif appeal.status == AppealStatus.COMPLETED:
            step4_status = "completed"
            step4_desc = f"Rasmiy javob tayyorlandi va taqdim etildi. {appeal.resolution_text or ''}"
        elif appeal.status == AppealStatus.REJECTED:
            step4_status = "rejected"
            step4_desc = f"Murojaat asosli sabablarga ko'ra rad etildi: {appeal.resolution_text or 'Normativ talablarga mos emas'}"

        steps.append(AppealTrackStep(
            step_key="resolved",
            title="Qaror va rasmiy hujjat tayyorlandi",
            description=step4_desc,
            status=step4_status,
            timestamp=appeal.resolved_at,
            actor_name=appeal.assigned_staff.full_name if appeal.assigned_staff else None,
            actor_role="Ijrochi",
            icon="file-certificate"
        ))

        # 5. COMPLETED / ARCHIVED
        if appeal.status == AppealStatus.COMPLETED:
            step5_status = "completed"
            rating_text = f" ({appeal.rating}/5 ball berildi)" if appeal.rating else ""
            step5_desc = f"Talaba xizmat natijasini tasdiqladi{rating_text}. Murojaat muvaffaqiyatli arxivlandi."
        elif appeal.status == AppealStatus.REJECTED:
            step5_status = "rejected"
            step5_desc = "Murojaat rad etilgan holatda yopildi."
        elif appeal.status == AppealStatus.RESOLVED:
            step5_status = "pending"
            step5_desc = "Talaba tomonidan natijani tasdiqlash va baholash kutilmoqda."
        else:
            step5_status = "pending"
            step5_desc = "Talaba tomonidan tasdiqlash."

        steps.append(AppealTrackStep(
            step_key="completed",
            title="Tasdiqlandi va arxivlandi",
            description=step5_desc,
            status=step5_status,
            timestamp=appeal.closed_at,
            actor_name="Talaba",
            actor_role="Murojaatchi",
            icon="badge-check"
        ))

        return steps

    @classmethod
    async def get_appeal_track_info(
        cls, db: AsyncSession, appeal_id: int, current_user: User
    ) -> Optional[AppealTrackInfoOut]:
        """Talabaning o'z arizasi bo'yicha to'liq vizual trek ma'lumotlari."""
        query = (
            select(Appeal)
            .where(Appeal.id == appeal_id)
            .options(
                selectinload(Appeal.service).selectinload(Service.department),
                selectinload(Appeal.assigned_staff),
                selectinload(Appeal.student)
            )
        )
        res = await db.execute(query)
        appeal = res.scalar_one_or_none()
        if not appeal:
            return None

        # Ruxsat tekshiruvi: faqat murojaat egasi yoki xodimlar ko'ra oladi
        if current_user.role.value == "student" and appeal.student_id != current_user.id:
            return None

        now = datetime.now(timezone.utc)
        queue_ahead = await cls._get_queue_ahead_count(db, appeal)
        est_text, is_work_time, progress_pct = cls._get_estimated_completion(appeal, queue_ahead, now)
        steps = cls._build_steps(appeal)

        # Status yorlig'i
        status_labels = {
            AppealStatus.NEW: "Yangi (qabul qilindi)",
            AppealStatus.ASSIGNED: "Xodimga biriktirildi",
            AppealStatus.IN_PROGRESS: "Ko'rib chiqilmoqda",
            AppealStatus.RESOLVED: "Hal etildi (tasdiqlash kutilmoqda)",
            AppealStatus.COMPLETED: "Bajarildi (tasdiqlangan)",
            AppealStatus.REJECTED: "Rad etildi",
            AppealStatus.DISPUTED: "E'tiroz bildirildi (nazoratda)",
            AppealStatus.ESCALATED_HEAD: "Ofis boshlig'i nazoratida",
            AppealStatus.ESCALATED_PROREKTOR: "Prorektor nazoratida",
        }

        dept_name = appeal.service.department.name if appeal.service and appeal.service.department else None
        staff_window = appeal.service.department.window_number if appeal.service and appeal.service.department else None

        return AppealTrackInfoOut(
            id=appeal.id,
            ticket_number=appeal.ticket_number,
            subject=appeal.subject,
            service_title=appeal.service.title if appeal.service else "Umumiy xizmat",
            service_department=dept_name,
            status=appeal.status,
            status_label=status_labels.get(appeal.status, appeal.status.value),
            progress_percentage=progress_pct,
            created_at=appeal.created_at,
            sla_deadline_at=appeal.sla_deadline_at,
            estimated_completion_text=est_text,
            queue_ahead_count=queue_ahead,
            is_working_hours=is_work_time,
            assigned_staff_name=appeal.assigned_staff.full_name if appeal.assigned_staff else None,
            assigned_staff_window=staff_window,
            resolution_text=appeal.resolution_text,
            result_file_url=appeal.result_file_url,
            qr_hash=appeal.qr_hash,
            rating=appeal.rating,
            rating_comment=appeal.rating_comment,
            steps=steps
        )

    @classmethod
    async def get_public_appeal_track(
        cls, db: AsyncSession, ticket_number: str
    ) -> Optional[AppealPublicTrackOut]:
        """Umumiy ochiq qidiruv: talaba shaxsiy ma'lumotlari maskalanadi (PII protection)."""
        clean_ticket = ticket_number.strip().upper()
        if not clean_ticket.startswith("#"):
            clean_ticket = "#" + clean_ticket

        query = (
            select(Appeal)
            .where(
                (Appeal.ticket_number == clean_ticket) | 
                (Appeal.ticket_number == clean_ticket.replace("#", ""))
            )
            .options(
                selectinload(Appeal.service),
                selectinload(Appeal.student)
            )
        )
        res = await db.execute(query)
        appeal = res.scalar_one_or_none()
        if not appeal:
            return None

        now = datetime.now(timezone.utc)
        queue_ahead = await cls._get_queue_ahead_count(db, appeal)
        est_text, is_work_time, progress_pct = cls._get_estimated_completion(appeal, queue_ahead, now)
        steps = cls._build_steps(appeal)

        status_labels = {
            AppealStatus.NEW: "Qabul qilindi",
            AppealStatus.ASSIGNED: "Biriktirildi",
            AppealStatus.IN_PROGRESS: "Ko'rib chiqilmoqda",
            AppealStatus.RESOLVED: "Hal etildi",
            AppealStatus.COMPLETED: "Bajarildi",
            AppealStatus.REJECTED: "Rad etildi",
            AppealStatus.DISPUTED: "E'tiroz bildirildi",
            AppealStatus.ESCALATED_HEAD: "Rahbariyat nazoratida",
            AppealStatus.ESCALATED_PROREKTOR: "Prorektor nazoratida",
        }

        masked_student = cls._mask_student_name(appeal.student.full_name if appeal.student else None)

        return AppealPublicTrackOut(
            ticket_number=appeal.ticket_number,
            subject=appeal.subject,
            service_title=appeal.service.title if appeal.service else "Davlat xizmati",
            student_masked_name=masked_student,
            status=appeal.status,
            status_label=status_labels.get(appeal.status, appeal.status.value),
            progress_percentage=progress_pct,
            created_at=appeal.created_at,
            estimated_completion_text=est_text,
            is_working_hours=is_work_time,
            steps=steps
        )
