from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import User, UserRole
from app.schemas import AuditLogOut
from app.api.deps import require_role
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Tizim xavfsizlik va audit jurnali"])


@router.get("", response_model=List[AuditLogOut], summary="Tizim harakatlar jurnali (faqat Rahbariyat va Admin uchun)")
async def get_audit_logs(
    entity_type: Optional[str] = Query(None, description="Obyekt turi (appeal, appointment, service, auth, staff)"),
    action: Optional[str] = Query(None, description="Amal turi (masalan, status_changed, assigned, login, prorektor_decision)"),
    search: Optional[str] = Query(None, description="Tafsilotlar bo'yicha qidiruv"),
    limit: int = Query(50, ge=1, le=200, description="Maksimal qaytariladigan yozuvlar soni"),
    offset: int = Query(0, ge=0, description="Surilish"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Tizimdagi barcha muhim xavfsizlik va ma'muriy amallar tarixini qaytaradi.
    Faqat Registrator ofisi boshlig'i, Prorektor va Admin kira oladi.
    """
    return await AuditService.get_logs(
        db=db,
        entity_type=entity_type,
        action=action,
        search=search,
        limit=limit,
        offset=offset
    )
