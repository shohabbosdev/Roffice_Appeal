from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import EmployeeKPITarget
from app.core.config import settings


class KPIService:
    @classmethod
    async def get_or_create_monthly_target(
        cls, db: AsyncSession, employee_id: int, period: Optional[str] = None
    ) -> EmployeeKPITarget:
        """Get or initialize monthly KPI record for an employee."""
        if not period:
            period = datetime.now(timezone.utc).strftime("%Y-%m")

        stmt = select(EmployeeKPITarget).where(
            EmployeeKPITarget.employee_id == employee_id,
            EmployeeKPITarget.period == period
        )
        result = await db.execute(stmt)
        kpi = result.scalars().first()

        if not kpi:
            kpi = EmployeeKPITarget(
                employee_id=employee_id,
                period=period,
                target_points=settings.DEFAULT_MONTHLY_KPI_TARGET,
                completed_points=0,
                penalty_points=0,
                total_appeals_completed=0,
                total_appointments_completed=0,
                average_rating=5.0,
                kpi_percentage=0.0
            )
            db.add(kpi)
            await db.commit()
            await db.refresh(kpi)

        return kpi

    @classmethod
    async def record_completed_service(
        cls,
        db: AsyncSession,
        employee_id: int,
        kpi_points: int,
        rating: Optional[int] = None,
        is_appointment: bool = False
    ) -> EmployeeKPITarget:
        """Award KPI points for completed service and recalculate percentage."""
        kpi = await cls.get_or_create_monthly_target(db, employee_id)

        kpi.completed_points += kpi_points
        if is_appointment:
            kpi.total_appointments_completed += 1
        else:
            kpi.total_appeals_completed += 1

        # Update average rating if rating provided
        total_rated = kpi.total_appeals_completed + kpi.total_appointments_completed
        if rating and 1 <= rating <= 5:
            current_sum = kpi.average_rating * (total_rated - 1)
            kpi.average_rating = round((current_sum + rating) / total_rated, 2)

        # Recalculate KPI percentage:
        # Net points = completed_points - penalty_points
        # Formula: (Net points / target_points) * (average_rating / 5.0) * 100
        net_points = max(0, kpi.completed_points - kpi.penalty_points)
        rating_factor = kpi.average_rating / 5.0
        kpi.kpi_percentage = round((net_points / kpi.target_points) * rating_factor * 100, 1)

        await db.commit()
        await db.refresh(kpi)
        return kpi

    @classmethod
    async def award_duty_points(
        cls, db: AsyncSession, employee_id: int, points: int
    ) -> EmployeeKPITarget:
        """Nizomiy xizmat vazifalari ijrosi yuzasidan xodimga KPI balli qo'shish."""
        kpi = await cls.get_or_create_monthly_target(db, employee_id)
        kpi.completed_points += points

        net_points = max(0, kpi.completed_points - kpi.penalty_points)
        rating_factor = kpi.average_rating / 5.0
        kpi.kpi_percentage = round((net_points / kpi.target_points) * rating_factor * 100, 1)

        await db.commit()
        await db.refresh(kpi)
        return kpi

    @classmethod
    async def apply_penalty(
        cls, db: AsyncSession, employee_id: int, penalty_points: int = 5
    ) -> EmployeeKPITarget:
        """Apply penalty points for overdue or missed SLA."""
        kpi = await cls.get_or_create_monthly_target(db, employee_id)
        kpi.penalty_points += penalty_points

        net_points = max(0, kpi.completed_points - kpi.penalty_points)
        rating_factor = kpi.average_rating / 5.0
        kpi.kpi_percentage = round((net_points / kpi.target_points) * rating_factor * 100, 1)

        await db.commit()
        await db.refresh(kpi)
        return kpi
