import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.api.deps import require_role
from app.services.backup_service import BackupService
from app.services.system_metrics import SystemMetricsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["Tizim va Monitoring"])


@router.get(
    "/metrics",
    summary="Tizim salomatligi va server resurslari ko'rsatkichlari",
    description="CPU, RAM, Disk, Server Uptime va Ma'lumotlar bazasi ko'rsatkichlarini real-vaqtda qaytaradi."
)
async def get_system_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Tizim monitoringi ko'rsatkichlari (Faqat Administrator uchun)."""
    start_time = getattr(request.app.state, "start_time", None)
    return await SystemMetricsService.get_full_system_status(db, start_time=start_time)


@router.get(
    "/backups",
    summary="Mavjud barcha zaxira nusxalari ro'yxati",
    description="Faqat Administrator uchun: Barcha yaratilgan zaxira arxivlari va ularning hajmi."
)
async def list_backups(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> List[Dict[str, Any]]:
    """Zaxiralar ro'yxati (Faqat Administrator)."""
    return BackupService.list_backups()


@router.post(
    "/backups",
    summary="Zudlik bilan yangi zaxira nusxasini yaratish",
    description="Faqat Administrator uchun: Ma'lumotlar bazasi va fayllarni arxivlaydi hamda Telegram orqali xabar beradi."
)
async def create_backup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Yangi zaxira yaratish."""
    try:
        result = await BackupService.create_backup(
            db=db,
            triggered_by=f"Admin: {current_user.full_name} (@{current_user.username})",
            user_id=current_user.id
        )
        return result
    except Exception as e:
        logger.error(f"Zaxira yaratishda kutilmagan xatolik: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Zaxira yaratish jarayonida xatolik yuz berdi: {str(e)}"
        )


@router.get(
    "/backups/{filename}/download",
    summary="Zaxira arxivini yuklab olish",
    description="Faqat Administrator uchun: Zaxira faylini (.tar.gz) xavfsiz yuklab beradi."
)
async def download_backup(
    filename: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Zaxira faylini yuklab olish."""
    try:
        file_path = BackupService.get_backup_path(filename)
        return FileResponse(
            path=str(file_path),
            media_type="application/gzip",
            filename=file_path.name
        )
    except (ValueError, PermissionError) as pe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Noto'g'ri yoki xavfsiz bo'lmagan fayl so'rovi: {str(pe)}"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="So'ralgan zaxira fayli serverda topilmadi."
        )
