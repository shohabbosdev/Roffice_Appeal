import os
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.models import Appeal, User, Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Hujjatlarni Ochiq Tekshirish (Public Verification)"])


@router.get(
    "/{qr_hash}",
    summary="QR-kod orqali hujjatning haqiqiyligini tekshirish",
    description="Ochiq kirish (Davlat idoralari va tashkilotlar uchun): QR-kod orqali berilgan ma'lumotnoma yoki ijro blankasining haqiqiyligini tasdiqlaydi."
)
async def verify_document_by_qr(
    qr_hash: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Hujjatning haqiqiyligini tekshiradi va akademik rekvizitlarni qaytaradi."""
    query = (
        select(Appeal)
        .options(
            selectinload(Appeal.student),
            selectinload(Appeal.service),
            selectinload(Appeal.assigned_staff)
        )
        .where(Appeal.qr_hash == qr_hash)
    )
    res = await db.execute(query)
    appeal = res.scalar_one_or_none()

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ushbu QR-kodga mos keluvchi rasmiy hujjat tizimda topilmadi. Hujjat mavjud emas yoki qalbakilashtirilgan bo'lishi mumkin."
        )

    student = appeal.student
    staff = appeal.assigned_staff
    service = appeal.service

    is_reference = "ma'lumotnoma" in (service.title.lower() if service else "") or "malumotnoma" in (service.code.lower() if service else "")
    doc_type = "Talabalik to'g'risida elektron ma'lumotnoma" if is_reference else "Murojaat bo'yicha rasmiy ijro blankasi"

    return {
        "verified": True,
        "status_text": "Hujjat haqiqiy va O'zMU Jizzax filiali tomonidan tasdiqlangan",
        "qr_hash": qr_hash,
        "doc_code": f"JBNUU-RO-{appeal.created_at.year if appeal.created_at else 2026}-{qr_hash[:8].upper()}",
        "document_type": doc_type,
        "ticket_number": appeal.ticket_number,
        "issued_at": appeal.resolved_at.isoformat() if appeal.resolved_at else (appeal.created_at.isoformat() if appeal.created_at else None),
        "student": {
            "full_name": student.full_name if student else "Noma'lum",
            "hemis_student_id": student.hemis_student_id if student else None,
            "faculty": student.faculty if student else None,
            "specialty": student.specialty if student else None,
            "course": student.course if student else None,
            "education_form": student.education_form if student else None,
            "education_type": student.education_type if student else "Bakalavriat",
        },
        "service": {
            "code": service.code if service else None,
            "title": service.title if service else "Registrator ofisi xizmati",
        },
        "resolution": {
            "status": appeal.status.value,
            "text": appeal.resolution_text,
            "staff_name": staff.full_name if staff else "Registrator ofisi",
            "pdf_url": appeal.result_file_url
        }
    }


@router.get(
    "/{qr_hash}/download",
    summary="Tasdiqlangan asl PDF hujjatni yuklab olish",
    description="Ochiq kirish: Verifikatsiya qilingan asl rasmiy PDF faylni yuklab beradi."
)
async def download_verified_pdf(
    qr_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """Asl PDF hujjatni uzatadi."""
    query = select(Appeal).where(Appeal.qr_hash == qr_hash)
    res = await db.execute(query)
    appeal = res.scalar_one_or_none()

    if not appeal or not appeal.result_file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hujjat topilmadi yoki uning fayli mavjud emas."
        )

    # Path traversal himoyasi
    clean_path = appeal.result_file_url.lstrip("/")
    base_uploads = Path(settings.UPLOAD_DIR).resolve()
    target_file = (Path(".") / clean_path).resolve()

    if not str(target_file).startswith(str(base_uploads)) and not "certificates" in str(target_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruxsatsiz fayl yo'li."
        )

    if not target_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF fayl serverda topilmadi."
        )

    return FileResponse(
        path=str(target_file),
        media_type="application/pdf",
        filename=target_file.name
    )
