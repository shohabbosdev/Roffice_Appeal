from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import EmployeeKPITarget, User, UserRole
from app.schemas import EmployeeKPIOut, KPIAwardRequest
from app.services.kpi_service import KPIService
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/kpi", tags=["KPI va Samaradorlik monitoringi"])


class PenalizeRequest(BaseModel):
    employee_id: int
    penalty_points: int = 5
    reason: str


@router.get("/my", response_model=EmployeeKPIOut, summary="Xodimning joriy oylik KPI ko'rsatkichlari")
async def get_my_kpi(
    period: Optional[str] = Query(None, description="Davr (YYYY-MM), masalan: 2026-09"),
    current_user: User = Depends(require_role(UserRole.FRONT_STAFF, UserRole.BACK_STAFF, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """Xodim o'zining to'plagan ballari, ijro etgan murojaatlari va foizini ko'radi."""
    kpi = await KPIService.get_or_create_monthly_target(db, current_user.id, period)
    res = await db.execute(
        select(EmployeeKPITarget).options(selectinload(EmployeeKPITarget.employee)).where(EmployeeKPITarget.id == kpi.id)
    )
    return res.scalar_one()


@router.get("/overview", response_model=List[EmployeeKPIOut], summary="Rahbariyat uchun barcha xodimlarning KPI hisoboti")
async def get_kpi_overview(
    period: Optional[str] = Query(None, description="Davr (YYYY-MM)"),
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.VICE_RECTOR, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Registrator ofisi boshlig'i va Prorektor barcha xodimlarning oylik standart (150 ball) bajarilishini kuzatadi."""
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")

    stmt = (
        select(EmployeeKPITarget)
        .options(selectinload(EmployeeKPITarget.employee))
        .where(EmployeeKPITarget.period == period)
        .order_by(EmployeeKPITarget.kpi_percentage.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/penalize", response_model=EmployeeKPIOut, summary="Muddati o'tgan yoki sifatsiz ijro uchun jarima balli qo'llash (-5 ball)")
async def apply_kpi_penalty(
    data: PenalizeRequest,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """SLA buzilganda xodimga jarima balli yoziladi va oylik reytingi kamaytiriladi."""
    target_user = await db.get(User, data.employee_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    kpi = await KPIService.apply_penalty(
        db=db,
        employee_id=data.employee_id,
        penalty_points=data.penalty_points
    )
    return kpi


@router.post("/award-points", response_model=EmployeeKPIOut, summary="Nizomiy xizmat vazifasini bajargani uchun xodimga KPI balli berish")
async def award_kpi_points(
    data: KPIAwardRequest,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Registrator ofisi boshlig'i yoki Admin xodimning nizomiy vazifalari bajarilishi bo'yicha KPI balli yozadi."""
    target_user = await db.get(User, data.employee_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    if target_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Talabalarga xizmat vazifalari KPI balli berilmaydi.")

    kpi = await KPIService.award_duty_points(
        db=db,
        employee_id=data.employee_id,
        points=data.points
    )
    return kpi
