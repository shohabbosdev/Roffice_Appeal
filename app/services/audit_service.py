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

    @staticmethod
    async def get_weekly_audit_report(db: AsyncSession) -> dict:
        """So'nggi 7 kunlik tizim harakatlari va xavfsizlik auditining umumiy tahlili."""
        from datetime import timedelta
        from sqlalchemy import func

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # 1. Jami loglar
        total_stmt = select(func.count(AuditLog.id)).where(AuditLog.created_at >= week_ago)
        total_logs = (await db.execute(total_stmt)).scalar() or 0

        # 2. Amallar bo'yicha guruhlash
        action_stmt = (
            select(AuditLog.action, func.count(AuditLog.id))
            .where(AuditLog.created_at >= week_ago)
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        action_res = await db.execute(action_stmt)
        actions_breakdown = {row[0]: row[1] for row in action_res.all()}

        # 3. Ob'ekt turlari bo'yicha guruhlash
        entity_stmt = (
            select(AuditLog.entity_type, func.count(AuditLog.id))
            .where(AuditLog.created_at >= week_ago)
            .group_by(AuditLog.entity_type)
            .order_by(func.count(AuditLog.id).desc())
        )
        entity_res = await db.execute(entity_stmt)
        entities_breakdown = {row[0]: row[1] for row in entity_res.all()}

        # 4. Eng faol foydalanuvchilar
        user_stmt = (
            select(AuditLog.user_id, func.count(AuditLog.id))
            .where(AuditLog.created_at >= week_ago, AuditLog.user_id.isnot(None))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(5)
        )
        user_res = await db.execute(user_stmt)
        top_users = [{"user_id": row[0], "actions_count": row[1]} for row in user_res.all()]

        return {
            "period": {
                "start": week_ago.isoformat(),
                "end": now.isoformat(),
                "days": 7
            },
            "total_audit_records": total_logs,
            "actions_breakdown": actions_breakdown,
            "entities_breakdown": entities_breakdown,
            "top_active_users": top_users,
            "system_health": "OPTIMAL" if total_logs >= 0 else "NO_DATA"
        }
