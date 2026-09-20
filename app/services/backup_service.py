import os
import json
import shutil
import tarfile
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Department, User, Service, EmployeeKPITarget, 
    Appeal, Appointment, AuditLog, Holiday, SystemSetting, user_services
)
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(getattr(settings, "BACKUP_DIR", "backups"))
MAX_BACKUP_RETENTION = 14


class BackupService:
    """Tizim ma'lumotlar bazasi va yuklangan hujjatlarni xavfsiz zaxiralash (Backup & Disaster Recovery) xizmati."""

    @staticmethod
    def ensure_backup_dir() -> Path:
        """Zaxira saqlanadigan katalogni mavjudligini ta'minlaydi."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return BACKUP_DIR

    @classmethod
    def _format_size(cls, size_bytes: int) -> str:
        """Fayl hajmini odam o'qiy oladigan formatga keltiradi."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @classmethod
    async def dump_database_json(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Universallik va relyatsion xavfsizlik uchun barcha jadvallardagi
        ma'lumotlarni to'liq JSON formatida eksport qiladi.
        """
        dump_data: Dict[str, Any] = {
            "version": settings.VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tables": {}
        }

        # Model mapping
        models = [
            ("departments", Department),
            ("users", User),
            ("services", Service),
            ("employee_kpi_targets", EmployeeKPITarget),
            ("appeals", Appeal),
            ("appointments", Appointment),
            ("holidays", Holiday),
            ("system_settings", SystemSetting),
            ("audit_logs", AuditLog),
        ]

        for table_name, model_cls in models:
            res = await db.execute(select(model_cls))
            records = res.scalars().all()
            table_rows = []
            for row in records:
                row_dict = {}
                for col in inspect(row).mapper.column_attrs:
                    val = getattr(row, col.key)
                    if isinstance(val, datetime):
                        row_dict[col.key] = val.isoformat()
                    elif hasattr(val, "value"):  # Enum
                        row_dict[col.key] = val.value
                    else:
                        row_dict[col.key] = val
                table_rows.append(row_dict)
            dump_data["tables"][table_name] = table_rows

        # user_services many-to-many jadvali
        us_res = await db.execute(select(user_services))
        dump_data["tables"]["user_services"] = [
            {"user_id": r.user_id, "service_id": r.service_id} for r in us_res.all()
        ]

        return dump_data

    @classmethod
    async def create_backup(
        cls, 
        db: AsyncSession, 
        triggered_by: str = "Tizim (Avtomatik)",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        To'liq zaxira nusxasini (.tar.gz) yaratadi:
        1. DB jadvallarini JSON formatda eksport qiladi;
        2. SQLite bo'lsa roffice.db faylini kiritadi;
        3. Uploads/ katalogidagi fayllarni kiritadi;
        4. Arxivlaydi va saqlaydi;
        5. Eskirgan (14 tadan oshiq) zaxiralarni tozalaydi;
        6. Telegram orqali xabardor qiladi.
        """
        cls.ensure_backup_dir()
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        temp_dir = BACKUP_DIR / f"temp_{timestamp_str}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        archive_filename = f"backup_roffice_{timestamp_str}.tar.gz"
        archive_path = BACKUP_DIR / archive_filename

        try:
            # 1. JSON dump yaratish
            db_data = await cls.dump_database_json(db)
            json_file = temp_dir / "database_dump.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(db_data, f, ensure_ascii=False, indent=2)

            # 2. Agar SQLite bo'lsa va mavjud bo'lsa, xom .db faylini ham nusxalash
            if "sqlite" in settings.DATABASE_URL:
                db_file_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
                if os.path.exists(db_file_path):
                    shutil.copy2(db_file_path, temp_dir / "database.sqlite")

            # 3. uploads/ papkasini qo'shish
            uploads_dir = Path(settings.UPLOAD_DIR)
            if uploads_dir.exists() and uploads_dir.is_dir():
                dest_uploads = temp_dir / "uploads"
                shutil.copytree(uploads_dir, dest_uploads, dirs_exist_ok=True)

            # Metadata fayl
            meta = {
                "backup_filename": archive_filename,
                "created_at": now.isoformat(),
                "triggered_by": triggered_by,
                "project": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "tables_count": {k: len(v) for k, v in db_data["tables"].items()}
            }
            with open(temp_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            # 4. .tar.gz arxivini yaratish
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in temp_dir.iterdir():
                    tar.add(item, arcname=item.name)

            file_size = archive_path.stat().st_size
            human_size = cls._format_size(file_size)

            # 5. Audit log yozish
            audit_log = AuditLog(
                user_id=user_id,
                entity_type="system",
                entity_id=0,
                action="backup_created",
                details=f"Zaxira nusxa yaratildi: {archive_filename} ({human_size}). Tashabbuskor: {triggered_by}"
            )
            db.add(audit_log)
            await db.commit()

            # 6. Eskirgan zaxiralarni tozalash (Retention policy)
            cleaned_count = cls.enforce_retention_policy()

            # 7. Telegram orqali adminlarga xabar yuborish
            await cls._notify_admins_on_backup(
                archive_filename=archive_filename,
                human_size=human_size,
                triggered_by=triggered_by,
                now=now,
                db=db
            )

            logger.info(f"Yangi zaxira yaratildi: {archive_filename} ({human_size})")

            return {
                "success": True,
                "filename": archive_filename,
                "size_bytes": file_size,
                "size_human": human_size,
                "created_at": now.isoformat(),
                "triggered_by": triggered_by,
                "cleaned_old_backups": cleaned_count
            }

        finally:
            # Vaqtinchalik fayllarni tozalash
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def list_backups(cls) -> List[Dict[str, Any]]:
        """Mavjud barcha zaxira nusxalari ro'yxatini qaytaradi."""
        cls.ensure_backup_dir()
        backups = []
        for file_path in BACKUP_DIR.glob("backup_roffice_*.tar.gz"):
            if file_path.is_file():
                stat = file_path.stat()
                created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                backups.append({
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "size_human": cls._format_size(stat.st_size),
                    "created_at": created_at.isoformat(),
                })
        # Eng yangi zaxiralarni yuqoriga chiqarish
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    @classmethod
    def get_backup_path(cls, filename: str) -> Path:
        """
        Path traversal zaifliklaridan himoyalangan holda
        fayl manzilini qaytaradi.
        """
        clean_filename = os.path.basename(filename)
        if not clean_filename.startswith("backup_roffice_") or not clean_filename.endswith(".tar.gz"):
            raise ValueError("Noto'g'ri zaxira fayl formati")

        target_path = (BACKUP_DIR / clean_filename).resolve()
        backup_dir_resolved = BACKUP_DIR.resolve()

        if not str(target_path).startswith(str(backup_dir_resolved)):
            raise PermissionError("Ruxsatsiz fayl yo'li (Path Traversal)")

        if not target_path.exists():
            raise FileNotFoundError("Zaxira fayli topilmadi")

        return target_path

    @classmethod
    def enforce_retention_policy(cls, max_keep: int = MAX_BACKUP_RETENTION) -> int:
        """Oxirgi `max_keep` ta zaxirani qoldirib, qolganlarini o'chiradi."""
        cls.ensure_backup_dir()
        files = sorted(
            list(BACKUP_DIR.glob("backup_roffice_*.tar.gz")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        deleted_count = 0
        if len(files) > max_keep:
            for old_file in files[max_keep:]:
                try:
                    old_file.unlink(missing_ok=True)
                    deleted_count += 1
                    logger.info(f"Eski zaxira o'chirildi (Retention): {old_file.name}")
                except Exception as e:
                    logger.error(f"Eski zaxirani o'chirishda xatolik ({old_file.name}): {e}")
        return deleted_count

    @classmethod
    def cleanup_old_backups(cls, days: int = 30) -> int:
        """Belgilangan kun (sukut bo'yicha 30 kun)dan oshgan eski zaxira nusxalarini diskdan tozalaydi."""
        cls.ensure_backup_dir()
        now_ts = datetime.now(timezone.utc).timestamp()
        cutoff_seconds = days * 86400
        deleted_count = 0

        for file_path in BACKUP_DIR.glob("backup_roffice_*.tar.gz"):
            if file_path.is_file():
                age_seconds = now_ts - file_path.stat().st_mtime
                if age_seconds > cutoff_seconds:
                    try:
                        file_path.unlink(missing_ok=True)
                        deleted_count += 1
                        logger.info(f"Eski zaxira fayli tozalandi (>{days} kun): {file_path.name}")
                    except Exception as e:
                        logger.error(f"Eski zaxirani tozalashda xatolik ({file_path.name}): {e}")
        return deleted_count

    @classmethod
    async def _notify_admins_on_backup(
        cls,
        archive_filename: str,
        human_size: str,
        triggered_by: str,
        now: datetime,
        db: AsyncSession
    ) -> None:
        """Administratorlarga Telegram orqali zaxira haqida ma'lumot jo'natadi."""
        msg = (
            "💾 <b>Tizim Zaxira Nusxasi Muvaffaqiyatli Yaratildi</b>\n\n"
            f"📦 <b>Fayl:</b> <code>{archive_filename}</code>\n"
            f"⚖️ <b>Hajmi:</b> {human_size}\n"
            f"👤 <b>Tashabbuskor:</b> {triggered_by}\n"
            f"🕒 <b>Vaqt:</b> {now.strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n"
            "✅ <i>Ma'lumotlar bazasi va biriktirilgan fayllar to'liq saqlandi.</i>"
        )
        try:
            # Adminlarni topish
            admin_res = await db.execute(
                select(User).where(User.role == "admin", User.telegram_chat_id.isnot(None))
            )
            admins = admin_res.scalars().all()
            for admin in admins:
                if admin.telegram_chat_id:
                    await TelegramService.send_telegram_message(
                        chat_id=admin.telegram_chat_id,
                        text=msg,
                        parse_mode="HTML"
                    )
        except Exception as e:
            logger.warning(f"Zaxira bildirishnomasini Telegram orqali yuborishda xatolik: {e}")


async def run_backup_scheduler_loop():
    """Har kecha Toshkent vaqti bilan soat 03:00 da (UTC+5) avtomatik zaxira oluvchi fon vazifasi."""
    import asyncio
    from datetime import timedelta
    from app.core.database import AsyncSessionLocal

    logger.info("Avtomatik zaxira rejalashtiruvchisi (Backup Scheduler) fon vazifasi ishga tushirildi.")
    last_backup_date = None

    while True:
        try:
            await asyncio.sleep(45)  # Har 45 soniyada tekshiradi
            now_utc = datetime.now(timezone.utc)
            tashkent_now = now_utc + timedelta(hours=5)
            today_str = tashkent_now.strftime("%Y-%m-%d")

            # Har kecha soat 03:00 da
            if tashkent_now.hour == 3 and tashkent_now.minute == 0 and last_backup_date != today_str:
                logger.info(f"Tungi avtomatik zaxiralash boshlandi ({today_str})...")
                async with AsyncSessionLocal() as db:
                    await BackupService.create_backup(
                        db=db,
                        triggered_by="Tungi avtomatik rejalashtiruvchi (03:00)"
                    )
                last_backup_date = today_str
        except asyncio.CancelledError:
            logger.info("Backup Scheduler fon vazifasi to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"Backup Scheduler fon siklida kutilmagan xatolik: {e}")
            await asyncio.sleep(60)

