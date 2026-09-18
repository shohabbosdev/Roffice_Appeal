"""
Registrator Ofisi - Administrator hisobini xavfsiz boshqarish skripti.
Hech qanday parol yoki maxfiy ma'lumot kodda ochiq saqlanmaydi.
Ma'lumotlar .env, muhit o'zgaruvchilari yoki parametrlar orqali uzatiladi.
"""
import asyncio
import os
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import hash_password
from app.models import User, UserRole


async def setup_admin(email: str = None, password: str = None, username: str = None, full_name: str = None):
    email = email or os.getenv("ADMIN_EMAIL")
    password = password or os.getenv("ADMIN_PASSWORD")
    username = username or os.getenv("ADMIN_USERNAME") or (email.split("@")[0] if email and "@" in email else "admin")
    full_name = full_name or os.getenv("ADMIN_FULLNAME") or "Tizim Administratori"

    if not email or not password:
        print("Xatolik: ADMIN_EMAIL va ADMIN_PASSWORD ko'rsatilishi shart!")
        sys.exit(1)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Search for existing user with this email, username, or role=ADMIN
        stmt = select(User).where(
            (User.email == email) | (User.username == username) | (User.role == UserRole.ADMIN)
        )
        admin = (await session.execute(stmt)).scalars().first()

        hashed = hash_password(password)
        if admin:
            admin.email = email
            admin.username = username
            admin.full_name = full_name
            admin.hashed_password = hashed
            admin.role = UserRole.ADMIN
            admin.is_active = True
            await session.commit()
            print(f"Administrator hisobi muvaffaqiyatli yangilandi: {email} (ID: {admin.id})")
        else:
            new_admin = User(
                username=username,
                email=email,
                full_name=full_name,
                hashed_password=hashed,
                role=UserRole.ADMIN,
                is_active=True
            )
            session.add(new_admin)
            await session.commit()
            print(f"Yangi administrator hisobi yaratildi: {email} (ID: {new_admin.id})")


if __name__ == "__main__":
    email_arg = sys.argv[1] if len(sys.argv) > 1 else None
    pass_arg = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(setup_admin(email_arg, pass_arg))
