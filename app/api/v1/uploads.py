import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/uploads", tags=["Fayl yuklash (Hujjatlar va Ilovalar)"])

# Uploads papkasini tayyorlash
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)


@router.post("", summary="Hujjat yoki tasdiqlovchi faylni serverga yuklash")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Murojaatlar, arizalar yoki xizmat natijasi uchun PDF, Word yoki rasm fayllarni yuklash.
    Maksimal hajm: 10 MB.
    Ruxsat etilgan formatlar: .pdf, .png, .jpg, .jpeg, .doc, .docx
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fayl tanlanmadi.")

    # Kengaytmani tekshirish
    _, ext = os.path.splitext(file.filename)
    ext_lower = ext.lower()
    if ext_lower not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Faqat quyidagi formatdagi fayllar qabul qilinadi: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Fayl tarkibini o'qish va hajmini tekshirish
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Fayl hajmi 10 MB dan oshmasligi kerak (joriy hajm: {file_size / (1024 * 1024):.1f} MB)."
        )

    # Xavfsiz unikal fayl nomi
    unique_filename = f"{uuid.uuid4().hex}{ext_lower}"
    file_dest = upload_path / unique_filename

    with open(file_dest, "wb") as f:
        f.write(content)

    file_url = f"/uploads/{unique_filename}"

    return {
        "success": True,
        "filename": unique_filename,
        "original_name": file.filename,
        "file_url": file_url,
        "size_bytes": file_size,
        "content_type": file.content_type
    }
