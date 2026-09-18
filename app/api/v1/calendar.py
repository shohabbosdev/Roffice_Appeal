from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import Holiday, User, UserRole
from app.schemas import HolidayCreate, HolidayOut
from app.api.deps import require_role

router = APIRouter(prefix="/calendar", tags=["Ish vaqti va Bayramlar kalendari"])


@router.get("/holidays", response_model=List[HolidayOut], summary="Rasmiy bayramlar va dam olish kunlari ro'yxati")
async def get_holidays(db: AsyncSession = Depends(get_db)):
    """Tizimda hisobga olinadigan barcha rasmiy bayramlar va qo'shimcha dam olish kunlari."""
    result = await db.execute(select(Holiday).order_by(Holiday.holiday_date))
    return result.scalars().all()


@router.post("/holidays", response_model=HolidayOut, status_code=status.HTTP_201_CREATED, summary="Yangi bayram yoki dam olish kunini kiritish (Boshliq / Admin)")
async def add_holiday(
    data: HolidayCreate,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Ofis boshlig'i yoki administrator rasmiy bayram yoki ko'chirilgan dam olish kunini kiritadi.
    Ushbu sanada murojaat taymerlari muzlaydi va elektron navbat berilmaydi.
    """
    stmt = select(Holiday).where(Holiday.holiday_date == data.holiday_date)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{data.holiday_date} sanasi bo'yicha bayram yozuvi allaqachon mavjud ({existing.title})."
        )

    holiday = Holiday(
        holiday_date=data.holiday_date,
        title=data.title,
        is_working_day=data.is_working_day
    )
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return holiday


@router.delete("/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Bayram kunini o'chirish (Boshliq / Admin)")
async def delete_holiday(
    holiday_id: int,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Kalendardan bayram yozuvini olib tashlash."""
    holiday = await db.get(Holiday, holiday_id)
    if not holiday:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bayram yozuvi topilmadi.")

    await db.delete(holiday)
    await db.commit()
    return None
