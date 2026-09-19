from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.models import AuditLog


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: Optional[int] = None,
        user: Optional[object] = None,
        details: Optional[str] = None,
        changes: Optional[object] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Tizimda harakat audit yozuvini yaratadi va saqlaydi."""
        import json

        if user is not None and user_id is None:
            user_id = getattr(user, "id", None)

        if details is None:
            parts = []
            if changes is not None:
                try:
                    parts.append(json.dumps(changes, ensure_ascii=False) if isinstance(changes, (dict, list)) else str(changes))
                except Exception:
                    parts.append(str(changes))
            if ip_address:
                parts.append(f"IP: {ip_address}")
            if parts:
                details = " | ".join(parts)

        log_entry = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        await db.flush()
        return log_entry

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuditLog]:
        """Tizim audit jurnali yozuvlarini foydalanuvchi ma'lumotlari bilan qaytaradi."""
        query = (
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .order_by(AuditLog.created_at.desc())
        )

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        if action:
            query = query.where(AuditLog.action == action)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    AuditLog.details.ilike(search_pattern),
                    AuditLog.action.ilike(search_pattern),
                    AuditLog.entity_type.ilike(search_pattern)
                )
            )

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())
