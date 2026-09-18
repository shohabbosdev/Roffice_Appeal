from datetime import datetime, timedelta, timezone
from typing import Optional, Set
from app.core.config import settings


class SLAService:
    @staticmethod
    def is_working_day(dt: datetime, holidays: Optional[Set[str]] = None) -> bool:
        """Check if date is a working day (Mon-Sat, excluding holidays)."""
        if dt.weekday() not in settings.WORK_DAYS:
            return False
        if holidays and dt.strftime("%Y-%m-%d") in holidays:
            return False
        return True

    @classmethod
    def is_working_time(cls, dt: datetime, holidays: Optional[Set[str]] = None) -> bool:
        """Check if datetime is within official working hours (Mon-Sat, 09:00 - 17:00, excluding lunch and holidays)."""
        if not cls.is_working_day(dt, holidays):
            return False
        if dt.hour == settings.LUNCH_START_HOUR:
            return False
        return settings.WORK_START_HOUR <= dt.hour < settings.WORK_END_HOUR

    @classmethod
    def calculate_deadline(
        cls, start_time: datetime, sla_hours: int, holidays: Optional[Set[str]] = None
    ) -> datetime:
        """
        Calculate SLA deadline by advancing time ONLY during working hours (Mon-Sat 09:00-17:00,
        excluding 13:00-14:00 lunch break and official holidays).
        """
        current = start_time.astimezone(timezone.utc)
        remaining_minutes = sla_hours * 60

        while remaining_minutes > 0:
            # 1. Dam olish kuni yoki ish vaqti tugagan bo'lsa -> keyingi ish kuni 09:00 ga o'tish
            while not cls.is_working_day(current, holidays) or current.hour >= settings.WORK_END_HOUR:
                current = (current + timedelta(days=1)).replace(
                    hour=settings.WORK_START_HOUR, minute=0, second=0, microsecond=0
                )

            # 2. Ertalabki 09:00 dan oldin bo'lsa -> shu kun 09:00 ga o'tish
            if current.hour < settings.WORK_START_HOUR:
                current = current.replace(hour=settings.WORK_START_HOUR, minute=0, second=0, microsecond=0)

            # 3. Tushlik tanaffusi oralig'ida bo'lsa -> 14:00 ga o'tish
            if settings.LUNCH_START_HOUR <= current.hour < settings.LUNCH_END_HOUR:
                current = current.replace(hour=settings.LUNCH_END_HOUR, minute=0, second=0, microsecond=0)

            # 4. Joriy ish oralig'i oxirini aniqlash (tushlikkacha yoki kun oxirigacha)
            if current.hour < settings.LUNCH_START_HOUR:
                interval_end = current.replace(hour=settings.LUNCH_START_HOUR, minute=0, second=0, microsecond=0)
            else:
                interval_end = current.replace(hour=settings.WORK_END_HOUR, minute=0, second=0, microsecond=0)

            available_minutes = int((interval_end - current).total_seconds() / 60)

            if remaining_minutes <= available_minutes:
                current = current + timedelta(minutes=remaining_minutes)
                remaining_minutes = 0
            else:
                remaining_minutes -= available_minutes
                current = interval_end

        return current

    @staticmethod
    def get_traffic_light(created_at: datetime, deadline: datetime, current_time: Optional[datetime] = None) -> str:
        """
        Returns traffic light status:
        - GREEN: < 50% time elapsed
        - YELLOW: 50% to 80% time elapsed
        - RED: > 80% or OVERDUE
        """
        now = current_time.astimezone(timezone.utc) if current_time else datetime.now(timezone.utc)
        total_seconds = (deadline - created_at).total_seconds()
        if total_seconds <= 0:
            return "RED"

        elapsed_seconds = (now - created_at).total_seconds()
        ratio = elapsed_seconds / total_seconds

        if ratio < 0.50:
            return "GREEN"
        elif ratio <= 0.80:
            return "YELLOW"
        else:
            return "RED"
