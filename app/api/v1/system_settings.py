from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import User, UserRole
from app.schemas import IntegrationSettingsOut, IntegrationSettingsUpdate
from app.api.deps import require_role
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/system", tags=["Tizim va integratsiya sozlamalari (Faqat Asosiy Administrator)"])


@router.get(
    "/integrations",
    response_model=IntegrationSettingsOut,
    summary="Telegram Bot va HEMIS integratsiya sozlamalarini ko'rish (Faqat Admin)"
)
async def get_integration_settings(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Faqat tizim Asosiy Administratori uchun:
    Telegram bot username, maskalangan token, Admin chat ID va HEMIS tokenni olish.
    Boshqa rollar (xodimlar, boshliqlar, prorektor) uchun qat'iyan taqiqlanadi (403).
    """
    return await IntegrationService.get_integration_settings(db, for_admin_ui=True)


@router.put(
    "/integrations",
    response_model=IntegrationSettingsOut,
    summary="Telegram Bot va HEMIS integratsiya sozlamalarini xavfsiz yangilash (Faqat Admin)"
)
async def update_integration_settings(
    data: IntegrationSettingsUpdate,
    request: Request,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Faqat tizim Asosiy Administratori uchun:
    Yangi Telegram Bot tokeni, bot username (@rofficejbnuubot), Admin Telegram ID
    hamda JBNUU HEMIS API tokenini kiritish va bazada xavfsiz shifrlab saqlash.
    Boshqa rollar (xodimlar, boshliqlar, prorektor) uchun qat'iyan taqiqlanadi (403).
    """
    ip_address = request.client.host if request.client else None
    update_dict = data.model_dump(exclude_unset=True)
    return await IntegrationService.update_integration_settings(
        db=db,
        data=update_dict,
        admin_user=current_user,
        ip_address=ip_address
    )
