import io
import csv
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Announcement, User, UserRole
from app.schemas import (
    AnnouncementCreate, AnnouncementOut, AnnouncementStudentView,
    AnnouncementAnalyticsOut
)
from app.services.announcement_service import AnnouncementService
from app.api.deps import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/announcements", tags=["E'lonlar va Xabarnomalar (Targeted Announcements)"])


@router.get("/my", response_model=List[AnnouncementStudentView], summary="Talabaga tegishli e'lonlar ro'yxati")
async def get_my_announcements(
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talabaning ta'lim shakli, fakulteti va bosqichiga mos keluvchi barcha faol e'lonlar."""
    return await AnnouncementService.get_announcements_for_student(db, current_user)


@router.post("/{announcement_id}/read", summary="E'lonni o'qildi yoki tanishdim deb qayd etish")
async def mark_announcement_read(
    announcement_id: int,
    request: Request,
    is_ack: bool = Query(False, description="Tanishdim tugmasi bosilganligi"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Talaba e'lon bilan tanishganda yoki 'Tanishdim' tugmasini bosganda fiksatsiya qiladi."""
    ip_addr = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:250]
    
    record = await AnnouncementService.mark_as_read(
        db=db,
        announcement_id=announcement_id,
        student_id=current_user.id,
        ip_address=ip_addr,
        user_agent=ua,
        is_acknowledged=is_ack
    )
    return {
        "status": "success",
        "announcement_id": announcement_id,
        "read_at": record.read_at.isoformat(),
        "is_acknowledged": record.is_acknowledged
    }


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED, summary="Yangi e'lon yaratish")
async def create_announcement(
    data: AnnouncementCreate,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim yoki admin tomonidan maqsadli e'lon chiqarish."""
    return await AnnouncementService.create_announcement(db, current_user.id, data)


@router.get("", response_model=List[AnnouncementOut], summary="Barcha chiqarilgan e'lonlar (Xodim/Admin)")
async def get_all_announcements(
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """Boshqaruv paneli uchun e'lonlar ro'yxati."""
    query = (
        select(Announcement)
        .options(selectinload(Announcement.author))
        .order_by(desc(Announcement.created_at))
    )
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{announcement_id}/analytics", response_model=AnnouncementAnalyticsOut, summary="E'lonning o'qilganlik analitikasi va o'qimaganlar ro'yxati")
async def get_announcement_analytics(
    announcement_id: int,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """E'lon qamrovi, o'qiganlar foizi va o'qimagan talabalar ro'yxati."""
    analytics = await AnnouncementService.get_announcement_analytics(db, announcement_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="E'lon topilmadi.")
    return analytics


@router.get("/{announcement_id}/unread-export", summary="O'qimagan talabalar ro'yxatini CSV formatida yuklab olish")
async def export_unread_students_csv(
    announcement_id: int,
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """O'qimagan talabalarni dekanat yoki tyutorlar uchun CSV fayl shaklida uzatadi."""
    analytics = await AnnouncementService.get_announcement_analytics(db, announcement_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="E'lon topilmadi.")

    unread_list = analytics["unread_students"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "T/r", "Talaba F.I.SH.", "HEMIS ID", "Guruhi", "Fakulteti",
        "Bosqich", "Ta'lim shakli", "Telefon raqami"
    ])

    for i, st in enumerate(unread_list, 1):
        writer.writerow([
            i,
            st["full_name"],
            st["hemis_student_id"],
            st["group_name"],
            st["faculty"],
            f"{st['course']}-bosqich",
            st["education_form"],
            st["phone"]
        ])

    csv_data = "\ufeff" + output.getvalue() # UTF-8 BOM Excel uchun
    filename = f"oqimagan_talabalar_elon_{announcement_id}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{announcement_id}", summary="E'lonni o'chirish yoki bekor qilish")
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin yoki ofis boshlig'i tomonidan e'lonni bekor qilish."""
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="E'lon topilmadi.")

    await db.delete(ann)
    await db.commit()
    return {"status": "success", "message": "E'lon muvaffaqiyatli o'chirildi."}
