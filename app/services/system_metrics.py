import os
import sys
import shutil
import platform
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User, Appeal, Appointment, AuditLog, Service, AppealStatus
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)


class SystemMetricsService:
    """Tashqi og'ir kutubxonalarsiz (Zero-Dependency) server va tizim holatini monitoring qilish xizmati."""

    @staticmethod
    def get_disk_metrics() -> Dict[str, Any]:
        """Disk xotirasi ko'rsatkichlari (shutil yordamida)."""
        try:
            total, used, free = shutil.disk_usage(".")
            percent_used = round((used / total) * 100, 1) if total > 0 else 0
            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_human": f"{total / (1024**3):.1f} GB",
                "used_human": f"{used / (1024**3):.1f} GB",
                "free_human": f"{free / (1024**3):.1f} GB",
                "percent_used": percent_used,
                "status": "warning" if percent_used > 85 else "healthy"
            }
        except Exception as e:
            logger.error(f"Disk metrikasini olishda xatolik: {e}")
            return {"error": str(e), "percent_used": 0, "status": "unknown"}

    @staticmethod
    def get_ram_metrics() -> Dict[str, Any]:
        """Operativ xotira (RAM) ko'rsatkichlari (Linux /proc/meminfo orqali)."""
        mem_info: Dict[str, int] = {}
        try:
            meminfo_path = Path("/proc/meminfo")
            if meminfo_path.exists():
                with open(meminfo_path, "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val_str = parts[1].strip().split()[0]
                            if val_str.isdigit():
                                mem_info[key] = int(val_str) * 1024  # kB to bytes

                total = mem_info.get("MemTotal", 0)
                available = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
                used = total - available if total >= available else 0
                percent = round((used / total) * 100, 1) if total > 0 else 0

                return {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": available,
                    "total_human": f"{total / (1024**2):.0f} MB",
                    "used_human": f"{used / (1024**2):.0f} MB",
                    "free_human": f"{available / (1024**2):.0f} MB",
                    "percent_used": percent,
                    "status": "warning" if percent > 90 else "healthy"
                }
        except Exception as e:
            logger.warning(f"/proc/meminfo o'qib bo'lmadi: {e}")

        # Linux bo'lmagan (masalan macOS lokal muhiti) yoki fallback
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "total_human": "N/A (OS-level)",
            "used_human": "N/A",
            "free_human": "N/A",
            "percent_used": 0,
            "status": "healthy"
        }

    @staticmethod
    def get_cpu_metrics() -> Dict[str, Any]:
        """CPU va yuklama (Load Average) ko'rsatkichlari."""
        cpu_count = os.cpu_count() or 1
        load_1, load_5, load_15 = (0.0, 0.0, 0.0)
        try:
            if hasattr(os, "getloadavg"):
                load_1, load_5, load_15 = os.getloadavg()
            elif Path("/proc/loadavg").exists():
                with open("/proc/loadavg", "r") as f:
                    parts = f.read().split()
                    load_1, load_5, load_15 = float(parts[0]), float(parts[1]), float(parts[2])
        except Exception as e:
            logger.warning(f"CPU load avg olinmadi: {e}")

        normalized_load_1 = round((load_1 / cpu_count) * 100, 1)

        return {
            "cores": cpu_count,
            "load_1m": round(load_1, 2),
            "load_5m": round(load_5, 2),
            "load_15m": round(load_15, 2),
            "percent_load": min(100.0, normalized_load_1),
            "status": "warning" if normalized_load_1 > 85 else "healthy"
        }

    @staticmethod
    def get_uptime_metrics(start_time: Optional[datetime]) -> Dict[str, Any]:
        """Server ishga tushganidan buyon o'tgan vaqt (Uptime)."""
        if not start_time:
            return {"uptime_str": "Noma'lum", "seconds": 0}

        now = datetime.now(timezone.utc)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        delta = now - start_time
        total_seconds = int(delta.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} kun")
        if hours > 0 or days > 0:
            parts.append(f"{hours} soat")
        parts.append(f"{minutes} daqiqa")
        parts.append(f"{seconds} soniya")

        return {
            "uptime_str": " ".join(parts),
            "started_at": start_time.isoformat(),
            "total_seconds": total_seconds
        }

    @classmethod
    async def get_db_metrics(cls, db: AsyncSession) -> Dict[str, Any]:
        """Ma'lumotlar bazasidagi asosiy ob'ektlar statistikasi."""
        try:
            total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
            total_students = (await db.execute(select(func.count(User.id)).where(User.role == "student"))).scalar() or 0
            total_staff = total_users - total_students

            total_appeals = (await db.execute(select(func.count(Appeal.id)))).scalar() or 0
            active_appeals = (await db.execute(
                select(func.count(Appeal.id)).where(Appeal.status.in_([
                    AppealStatus.NEW, AppealStatus.ASSIGNED, AppealStatus.IN_PROGRESS, AppealStatus.CLARIFICATION_NEEDED
                ]))
            )).scalar() or 0
            resolved_appeals = (await db.execute(
                select(func.count(Appeal.id)).where(Appeal.status.in_([
                    AppealStatus.RESOLVED, AppealStatus.COMPLETED, AppealStatus.AUTO_CLOSED
                ]))
            )).scalar() or 0

            total_appointments = (await db.execute(select(func.count(Appointment.id)))).scalar() or 0
            total_audit_logs = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
            total_services = (await db.execute(select(func.count(Service.id)))).scalar() or 0

            return {
                "total_users": total_users,
                "total_students": total_students,
                "total_staff": total_staff,
                "total_appeals": total_appeals,
                "active_appeals": active_appeals,
                "resolved_appeals": resolved_appeals,
                "total_appointments": total_appointments,
                "total_audit_logs": total_audit_logs,
                "total_services": total_services,
                "database_engine": "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite"
            }
        except Exception as e:
            logger.error(f"DB metrikalarini hisoblashda xatolik: {e}")
            return {"error": str(e)}

    @classmethod
    async def get_full_system_status(
        cls, 
        db: AsyncSession, 
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Barcha server va tizim salomatligi metrikalarini to'liq to'playdi."""
        disk = cls.get_disk_metrics()
        ram = cls.get_ram_metrics()
        cpu = cls.get_cpu_metrics()
        uptime = cls.get_uptime_metrics(start_time)
        db_stats = await cls.get_db_metrics(db)
        backups = BackupService.list_backups()

        latest_backup = backups[0] if backups else None

        # Tizim umumiy salomatlik darajasi
        statuses = [disk.get("status"), ram.get("status"), cpu.get("status")]
        overall_status = "warning" if "warning" in statuses else "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "os": platform.system(),
                "os_release": platform.release(),
                "python_version": platform.python_version(),
                "project_version": settings.VERSION,
            },
            "uptime": uptime,
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "database": db_stats,
            "backups": {
                "total_backups": len(backups),
                "latest_backup": latest_backup
            }
        }
