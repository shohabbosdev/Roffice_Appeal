import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models import Announcement, AnnouncementRead, AnnouncementPriority, User, UserRole
from app.schemas import AnnouncementCreate
from app.services.telegram_service import TelegramService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnnouncementService:
    """Registrator ofisi ommaviy va segmentatsiyalangan e'lonlar xizmati."""

    @classmethod
    async def create_announcement(
        cls,
        db: AsyncSession,
        author_id: int,
        data: AnnouncementCreate
    ) -> Announcement:
        """Yangi maqsadli e'lon yaratish va ixtiyoriy Telegram signal yuborish."""
        announcement = Announcement(
            title=data.title,
            content=data.content,
            priority=data.priority,
            target_education_form=data.target_education_form if data.target_education_form and data.target_education_form != "ALL" else None,
            target_faculty=data.target_faculty if data.target_faculty and data.target_faculty != "ALL" else None,
            target_course=data.target_course if data.target_course and data.target_course != 0 else None,
            author_id=author_id,
            requires_ack=data.requires_ack,
            send_telegram=data.send_telegram,
            expires_at=data.expires_at,
            is_active=True
        )
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)

        # Agar Telegram orqali signal yuborish belgilangan bo'lsa
        if data.send_telegram and settings.TELEGRAM_BOT_TOKEN:
            try:
                await cls._dispatch_telegram_notifications(db, announcement)
            except Exception as e:
                logger.error(f"E'lon bo'yicha Telegram signal yuborishda xatolik: {e}")

        return announcement

    @classmethod
    async def _dispatch_telegram_notifications(cls, db: AsyncSession, ann: Announcement):
        """Maqsadli auditoriyadagi barcha telegram_chat_id ga ega talabalarga qisqa xabar yuborish."""
        query = select(User).where(
            User.role == UserRole.STUDENT,
            User.is_active == True,
            User.telegram_chat_id.isnot(None)
        )

        if ann.target_education_form:
            query = query.where(User.education_form == ann.target_education_form)
        if ann.target_faculty:
            query = query.where(User.faculty == ann.target_faculty)
        if ann.target_course:
            query = query.where(User.course == ann.target_course)

        res = await db.execute(query)
        target_students = res.scalars().all()

        prio_icon = "📢"
        if ann.priority == AnnouncementPriority.IMPORTANT:
            prio_icon = "⚠️"
        elif ann.priority == AnnouncementPriority.URGENT:
            prio_icon = "🚨"

        msg = (
            f"{prio_icon} <b>Registrator ofisi muhim e'loni!</b>\n\n"
            f"<b>Mavzu:</b> {ann.title}\n\n"
            f"<i>Hurmatli talaba, e'lonning to'liq matni bilan tanishish va tasdiqlash uchun "
            f"Registrator ofisi rasmiy portaliga kiring:</i>\n"
            f"🔗 <a href='https://jbnuu.uz/roffice-appeal/student'>https://jbnuu.uz/roffice-appeal/student</a>"
        )

        for st in target_students:
            try:
                await TelegramService.send_telegram_message(
                    chat_id=st.telegram_chat_id,
                    text=msg,
                    parse_mode="HTML"
                )
            except Exception:
                pass

    @classmethod
    async def get_announcements_for_student(
        cls,
        db: AsyncSession,
        student: User
    ) -> List[Dict[str, Any]]:
        """Talabaga tegishli barcha faol e'lonlarni va ularning o'qilganlik holatini qaytaradi."""
        now = datetime.now(timezone.utc)
        
        # Talabaga mos keluvchi filtrlash
        conditions = [
            Announcement.is_active == True,
            or_(Announcement.expires_at.is_(None), Announcement.expires_at > now),
            or_(Announcement.target_education_form.is_(None), Announcement.target_education_form == student.education_form),
            or_(Announcement.target_faculty.is_(None), Announcement.target_faculty == student.faculty),
            or_(Announcement.target_course.is_(None), Announcement.target_course == student.course),
        ]

        query = (
            select(Announcement)
            .where(and_(*conditions))
            .order_by(desc(Announcement.created_at))
        )
        res = await db.execute(query)
        announcements = res.scalars().all()

        if not announcements:
            return []

        # Talabaning o'qiganlik yozuvlarini olish
        ann_ids = [a.id for a in announcements]
        read_query = select(AnnouncementRead).where(
            AnnouncementRead.announcement_id.in_(ann_ids),
            AnnouncementRead.student_id == student.id
        )
        read_res = await db.execute(read_query)
        reads_map = {r.announcement_id: r for r in read_res.scalars().all()}

        result = []
        for a in announcements:
            read_info = reads_map.get(a.id)
            result.append({
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "priority": a.priority,
                "requires_ack": a.requires_ack,
                "created_at": a.created_at,
                "is_read": read_info is not None,
                "read_at": read_info.read_at if read_info else None,
                "is_acknowledged": read_info.is_acknowledged if read_info else False
            })

        return result

    @classmethod
    async def mark_as_read(
        cls,
        db: AsyncSession,
        announcement_id: int,
        student_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_acknowledged: bool = False
    ) -> AnnouncementRead:
        """Talabaning e'lonni o'qiganligini va/yoki tasdiqlaganligini qayd etish."""
        query = select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.student_id == student_id
        )
        res = await db.execute(query)
        read_record = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if read_record:
            if is_acknowledged and not read_record.is_acknowledged:
                read_record.is_acknowledged = True
                read_record.read_at = now
            if ip_address:
                read_record.ip_address = ip_address
            if user_agent:
                read_record.user_agent = user_agent[:250]
        else:
            read_record = AnnouncementRead(
                announcement_id=announcement_id,
                student_id=student_id,
                read_at=now,
                ip_address=ip_address,
                user_agent=user_agent[:250] if user_agent else None,
                is_acknowledged=is_acknowledged
            )
            db.add(read_record)

        await db.commit()
        await db.refresh(read_record)
        return read_record

    @classmethod
    async def get_announcement_analytics(
        cls,
        db: AsyncSession,
        announcement_id: int
    ) -> Optional[Dict[str, Any]]:
        """E'lon bo'yicha jonli qamrov, o'qiganlar va o'qimagan talabalar ro'yxatini hisoblash."""
        ann = await db.get(Announcement, announcement_id)
        if not ann:
            return None

        # 1. Maqsadli auditoriyadagi barcha faol talabalarni aniqlash
        q = select(User).where(
            User.role == UserRole.STUDENT,
            User.is_active == True
        )
        if ann.target_education_form:
            q = q.where(User.education_form == ann.target_education_form)
        if ann.target_faculty:
            q = q.where(User.faculty == ann.target_faculty)
        if ann.target_course:
            q = q.where(User.course == ann.target_course)

        target_students = (await db.execute(q)).scalars().all()
        total_count = len(target_students)

        # 2. Ushbu e'lonni o'qigan yozuvlar
        reads_q = select(AnnouncementRead).where(AnnouncementRead.announcement_id == announcement_id)
        reads = (await db.execute(reads_q)).scalars().all()
        read_student_ids = {r.student_id for r in reads}
        ack_student_ids = {r.student_id for r in reads if r.is_acknowledged}

        read_count = len(read_student_ids)
        ack_count = len(ack_student_ids)
        read_pct = round((read_count / total_count * 100), 1) if total_count > 0 else 0.0
        ack_pct = round((ack_count / total_count * 100), 1) if total_count > 0 else 0.0

        # 3. O'qimagan talabalar
        unread_students = []
        for st in target_students:
            if st.id not in read_student_ids:
                unread_students.append({
                    "id": st.id,
                    "full_name": st.full_name,
                    "hemis_student_id": st.hemis_student_id or st.username,
                    "group_name": st.group_name or "Mavjud emas",
                    "faculty": st.faculty or "Mavjud emas",
                    "course": st.course or 1,
                    "education_form": st.education_form or "Kunduzgi",
                    "phone": st.phone or "—"
                })

        return {
            "announcement": ann,
            "total_target_students": total_count,
            "read_count": read_count,
            "read_percentage": read_pct,
            "acknowledged_count": ack_count,
            "acknowledged_percentage": ack_pct,
            "unread_students": unread_students
        }
