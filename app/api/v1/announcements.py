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


@router.get("/{announcement_id}/unread-export", summary="O'qimagan talabalar ro'yxatini Excel (.xls) yoki CSV formatida yuklab olish")
async def export_unread_students_csv(
    announcement_id: int,
    format: str = Query("xls", description="Fayl formati: 'xls' yoki 'csv'"),
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """O'qimagan talabalarni dekanat yoki tyutorlar uchun formatlangan Excel (.xls) yoki CSV fayl shaklida uzatadi."""
    analytics = await AnnouncementService.get_announcement_analytics(db, announcement_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="E'lon topilmadi.")

    unread_list = analytics["unread_students"]
    ann_title = analytics.get("title", f"E'lon #{announcement_id}")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "T/r", "Talaba F.I.SH.", "HEMIS ID", "Guruhi", "Fakulteti",
            "Bosqich", "Ta'lim shakli", "Telefon raqami"
        ])
        for i, st in enumerate(unread_list, 1):
            writer.writerow([
                i, st["full_name"], st["hemis_student_id"], st["group_name"],
                st["faculty"], f"{st['course']}-bosqich", st["education_form"], st["phone"]
            ])
        csv_data = "\ufeff" + output.getvalue()
        filename = f"oqimagan_talabalar_elon_{announcement_id}.csv"
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    # Formatlangan Excel (.xls) HTML/XML Spreadsheet
    rows_html = ""
    for i, st in enumerate(unread_list, 1):
        zebra = "#ffffff" if i % 2 == 0 else "#f8fafc"
        rows_html += f"""
        <tr style="background-color: {zebra};">
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; text-align: center; font-size: 10pt;">{i}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; font-weight: bold; font-size: 10pt;">{st['full_name']}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; mso-number-format: '\\@'; font-size: 10pt;">{st['hemis_student_id']}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; text-align: center; font-size: 10pt;">{st['group_name']}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; font-size: 10pt;">{st['faculty']}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; text-align: center; font-size: 10pt;">{st['course']}-bosqich</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; text-align: center; font-size: 10pt;">{st['education_form']}</td>
            <td style="border: 1px solid #cbd5e1; padding: 6px 10px; mso-number-format: '\\@'; font-size: 10pt;">{st['phone'] or '—'}</td>
        </tr>
        """

    xls_content = f"""\ufeff<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; }}
            .title-hdr {{ background-color: #1e3a8a; color: #ffffff; font-size: 13pt; font-weight: bold; text-align: center; height: 38px; }}
            .meta-hdr {{ background-color: #f8fafc; color: #334155; font-size: 9.5pt; height: 24px; padding: 4px 8px; }}
            .th-hdr {{ background-color: #2563eb; color: #ffffff; font-size: 10pt; font-weight: bold; text-align: center; border: 1px solid #1d4ed8; height: 30px; }}
        </style>
    </head>
    <body>
        <table>
            <tr><td colspan="8" class="title-hdr">JIZZAX DAVLAT PEDAGOGIKA UNIVERSITETI - REGISTRATOR OFISI</td></tr>
            <tr><td colspan="8" class="meta-hdr">E'lon mavzusi: {ann_title}</td></tr>
            <tr><td colspan="8" class="meta-hdr">Hujjat turi: E'lon bilan tanishmagan talabalar ro'yxati (Jami: {len(unread_list)} nafar)</td></tr>
            <tr><td colspan="8" style="height: 10px;"></td></tr>
            <tr>
                <th class="th-hdr" style="width: 40px;">T/r</th>
                <th class="th-hdr" style="width: 250px;">Talaba F.I.SH.</th>
                <th class="th-hdr" style="width: 120px;">HEMIS ID</th>
                <th class="th-hdr" style="width: 100px;">Guruhi</th>
                <th class="th-hdr" style="width: 200px;">Fakulteti</th>
                <th class="th-hdr" style="width: 90px;">Bosqich</th>
                <th class="th-hdr" style="width: 110px;">Ta'lim shakli</th>
                <th class="th-hdr" style="width: 140px;">Telefon raqami</th>
            </tr>
            {rows_html}
        </table>
    </body>
    </html>
    """

    filename = f"oqimagan_talabalar_elon_{announcement_id}.xls"
    return Response(
        content=xls_content,
        media_type="application/vnd.ms-excel",
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
