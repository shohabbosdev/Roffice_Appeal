"""Production ma'lumotlar bazasidagi dastlabki sinov (mock) talabalar va ularning soxta arizalarini tozalash skripti.

Haqiqiy HEMIS talabalari (masalan, 401251200032, 401231100128, 401231100103) va ularning ma'lumotlariga
mutlaqo tegilmaydi.
"""
import asyncio
import os
import sys

# Project root pathni qo'shish
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models import User, Appeal, Appointment, AuditLog, UserRole


MOCK_STUDENT_USERNAMES = ["student_azamat", "student_shahlo", "student_mock_temp"]
MOCK_HEMIS_IDS = ["HEMIS-2024-101", "HEMIS-2024-102", "HEMIS-MOCK-TEMP"]


async def _do_cleanup(db: AsyncSession):
    # 1. Mock talabalarni aniqlash
    stmt = select(User).where(
        (User.username.in_(MOCK_STUDENT_USERNAMES)) |
        (User.hemis_student_id.in_(MOCK_HEMIS_IDS))
    )
    mock_students = (await db.execute(stmt)).scalars().all()
    mock_user_ids = [u.id for u in mock_students]

    if not mock_user_ids:
        print("✅ Bazada o'chirilishi kerak bo'lgan mock talabalar topilmadi. Baza toza!")
        return

    print(f"Topilgan mock talabalar soni: {len(mock_students)}")
    for u in mock_students:
        print(f" - ID: {u.id} | Username: {u.username} | F.I.Sh: {u.full_name}")

    # 2. Ularga bog'liq audit loglarni tozalash
    stmt_audit = delete(AuditLog).where(AuditLog.user_id.in_(mock_user_ids))
    res_audit = await db.execute(stmt_audit)
    print(f"O'chirilgan mock audit loglar soni: {res_audit.rowcount}")

    # 3. Ularga bog'liq elektron navbatlarni tozalash
    stmt_apt = delete(Appointment).where(Appointment.student_id.in_(mock_user_ids))
    res_apt = await db.execute(stmt_apt)
    print(f"O'chirilgan mock navbatlar soni: {res_apt.rowcount}")

    # 4. Ularga bog'liq arizalarni (Appeals) tozalash
    stmt_appeal = delete(Appeal).where(Appeal.student_id.in_(mock_user_ids))
    res_appeal = await db.execute(stmt_appeal)
    print(f"O'chirilgan mock arizalar soni: {res_appeal.rowcount}")

    # 5. Mock talaba hisoblarini o'chirish
    stmt_users = delete(User).where(User.id.in_(mock_user_ids))
    res_users = await db.execute(stmt_users)
    print(f"O'chirilgan mock foydalanuvchilar soni: {res_users.rowcount}")

    await db.commit()
    print("🎉 Barcha mock ma'lumotlar muvaffaqiyatli tozalandi!")


async def cleanup_mock_data(db: AsyncSession | None = None):
    print("🧹 Tizimdagi mock/sinov ma'lumotlarini tozalash boshlandi...")
    if db is not None:
        await _do_cleanup(db)
    else:
        async with AsyncSessionLocal() as session:
            await _do_cleanup(session)


if __name__ == "__main__":
    asyncio.run(cleanup_mock_data())
