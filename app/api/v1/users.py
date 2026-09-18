import secrets
import string
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models import User, UserRole
from app.schemas import (
    UserOut, UserRoleUpdate, StaffCreate, StaffCreateResponse,
    StaffUpdate, UpdateCredentialsRequest
)
from app.api.deps import require_role, get_current_user

router = APIRouter(prefix="/users", tags=["Foydalanuvchilar va rollar boshqaruvi"])


# Nizom bo'yicha namunaviy xizmat vazifalari katalogi
NIZOM_DUTIES_CATALOG = [
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Talabalarga xizmat ko'rsatish va ma'lumotnomalar sektori (1-darcha)",
        "duties": [
            "O'qish joyidan QR-kodli elektron ma'lumotnoma rasmiylashtirish",
            "Transkript va akademik ko'chirmalarni talabaga taqdim etish",
            "Diplom va uning ilovasini buyurtma qilish va berish",
            "Darcha qabulida elektron navbat taloni bo'yicha xizmat ko'rsatish"
        ]
    },
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Shartnoma, to'lovlar va stipendiya masalalari sektori (2-darcha)",
        "duties": [
            "To'lov-kontrakt shartnomalarini rasmiylashtirish va qaydnoma yuritish",
            "Talabalar stipendiyasi va moddiy yordam arizalarini birlamchi qabul qilish",
            "Kontrakt to'lovlari auditini muvofiqlashtirish"
        ]
    },
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Maslahat, qabul va umumiy arizalar sektori (3-darcha)",
        "duties": [
            "O'qishni ko'chirish (Perevod) arizalarini qabul qilish va ekspertiza qilish",
            "Akademik ta'tildan qaytish arizalarini ko'rib chiqish",
            "Kreditlarni qayta topshirish (qayta o'qish) arizalarini rasmiylashtirish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "O'quv jarayonini tahlil qilish va nazorat sektori",
        "duties": [
            "O'quv rejalari bajarilishini audit qilish va dars jadvallarini nazorat qilish",
            "Chetlatilgan talabalarni o'qishga qayta tiklash buyruqlarini tayyorlash",
            "Kursdan kursga o'tkazish buyruqlari loyihalarini ishlab chiqish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "Reyting va baholash sektori",
        "duties": [
            "Baholash vedomostlari va reyting jurnallarining to'g'riligini tekshirish",
            "Reyting qaydnomalari bo'yicha apellatsiyalarni ekspertiza qilish",
            "Talabalarning GPA ko'rsatkichlari va akademik qarzdorliklarini tahlil qilish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "HEMIS tizimi va AKT integratsiyasi sektori",
        "duties": [
            "HEMIS axborot tizimida talabalar o'quv dasturlari va fan tanlovlarini sozlash",
            "Elektron platforma integratsiyasi xatoliklarini bartaraf etish",
            "Elektron navbat tizimi texnik barqarorligini ta'minlash"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "Hujjatlar aylanishi va arxiv sektori",
        "duties": [
            "Bitiruvchilar va talabalarning shaxsiy yig'majildlari hamda arxivini yuritish",
            "Arxivdan o'quv reja, dastur va diplom tasdiqnomalarini tayyorlash"
        ]
    },
    {
        "role": UserRole.OFFICE_HEAD.value,
        "sector": "Registrator ofisi rahbariyati",
        "duties": [
            "Registrator ofisi faoliyatini umumiy boshqarish va xodimlar o'rtasida vazifalar taqsimlash",
            "Murojaatlar ijro muddati (SLA) va elektron navbat sifatini nazorat qilish",
            "Xodimlarning oylik KPI samaradorlik ko'rsatkichlarini baholash va rag'batlantirish",
            "Bahsli murojaatlarni tahlil qilish va prorektorga eskalatsiya qilish"
        ]
    },
    {
        "role": UserRole.VICE_RECTOR.value,
        "sector": "O'quv ishlari bo'yicha prorektorat",
        "duties": [
            "Eskalatsiya qilingan bahsli akademik murojaatlar bo'yicha yakuniy qaror qabul qilish",
            "Talabalar appelyatsiya komissiyasi faoliyatiga rahbarlik qilish"
        ]
    }
]


@router.get("/nizom-duties", summary="Registrator ofisi nizomi bo'yicha xizmat vazifalari katalogi")
async def get_nizom_duties(current_user: User = Depends(get_current_user)):
    """Nizomda belgilangan barcha sohalar va xizmat vazifalari ro'yxati."""
    return NIZOM_DUTIES_CATALOG


@router.get("/staff", response_model=List[UserOut], summary="Barcha xodimlar va ularning joriy rollari ro'yxati")
async def get_staff_list(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """Admin yoki Boshliq uchun barcha xodimlarni ko'rish va boshqarish ro'yxati."""
    result = await db.execute(
        select(User).where(User.role != UserRole.STUDENT).order_by(User.id.asc())
    )
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserOut, summary="Bitta xodimning to'liq ma'lumotlari")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return user


@router.post("/staff", response_model=StaffCreateResponse, status_code=status.HTTP_201_CREATED, summary="Yangi xodim qo'shish (bir martalik 8 belgili parol bilan)")
async def create_staff(
    data: StaffCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin yoki Boshliq tomonidan tizimga yangi xodim qo'shish.
    Xodim uchun avtomatik ravishda 8 belgili bir martalik parol (OTP) generatsiya qilinadi.
    Xodim birinchi marta tizimga kirganida ushbu parolni yangi shaxsiy paroliga almashtirishi shart.
    """
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ushbu login band.")

    # 8-character secure alphanumeric OTP generation
    if data.custom_password and len(data.custom_password.strip()) >= 8:
        temporary_password = data.custom_password.strip()
    else:
        chars = string.ascii_letters + string.digits
        temporary_password = "".join(secrets.choice(chars) for _ in range(8))

    new_staff = User(
        username=data.username,
        hashed_password=hash_password(temporary_password),
        full_name=data.full_name,
        role=data.role,
        department_id=data.department_id,
        email=data.email,
        phone=data.phone,
        assigned_duties=data.assigned_duties,
        must_change_password=True,
        is_active=True
    )
    db.add(new_staff)
    await db.commit()
    await db.refresh(new_staff)

    return StaffCreateResponse(
        user=new_staff,
        temporary_password=temporary_password,
        must_change_password=True
    )


@router.put("/{user_id}", response_model=UserOut, summary="Xodim ma'lumotlari va xizmat vazifalarini to'liq tahrirlash")
async def update_staff(
    user_id: int,
    data: StaffUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """Admin yoki Boshliq tomonidan xodim ma'lumotlarini, rolini yoki biriktirilgan xizmat vazifalarini yangilash."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.phone is not None:
        user.phone = data.phone
    if data.department_id is not None:
        user.department_id = data.department_id
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.assigned_duties is not None:
        user.assigned_duties = data.assigned_duties

    # Agar admin parolni qayta tiklashni so'rasa
    if data.reset_password:
        chars = string.ascii_letters + string.digits
        new_otp = "".join(secrets.choice(chars) for _ in range(8))
        user.hashed_password = hash_password(new_otp)
        user.must_change_password = True

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserOut, summary="Xodimning rolini admin tomonidan o'zgartirish")
async def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """Xodimga rolni admin profilidan berish."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")

    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", summary="Xodimni tizimdan o'chirish / nofaol qilish")
async def delete_staff(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """Xodimni tizimdan o'chirish (o'zini o'zi o'chirish taqiqlanadi)."""
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator o'z hisobini o'chira olmaydi.")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    user.is_active = False
    await db.commit()
    return {"message": f"Xodim ({user.full_name}) muvaffaqiyatli nofaol qilindi."}


@router.put("/me/credentials", summary="Har bir xodim o'z login va parolini mustaqil o'zgartirishi")
async def update_my_credentials(
    data: UpdateCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Xodim (talabadan tashqari) o'z joriy parolini kiritib, istalgan paytda:
    - Yangi foydalanuvchi logini;
    - Yangi shaxsiy maxfiy parol o'rnatishi mumkin.
    
    Talabalar uchun login va parol HEMIS orqali boshqariladi va bu yerda o'zgartirilmaydi.
    """
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Talabalar login va paroli HEMIS tizimi orqali boshqariladi. O'zgartirish talabaning shaxsiy HEMIS kabinetida amalga oshiriladi."
        )

    # 1. Joriy parolni tekshirish
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amaldagi maxfiy parol noto'g'ri kiritildi."
        )

    # 2. Yangi login tekshiruvi (agar ko'rsatilgan bo'lsa)
    if data.new_username and data.new_username.strip():
        new_u = data.new_username.strip()
        if new_u != current_user.username:
            stmt = select(User).where(User.username == new_u)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ushbu login boshqa xodim tomonidan band qilingan."
                )
            current_user.username = new_u

    # 3. Yangi parol tekshiruvi
    if data.new_password and data.new_password.strip():
        new_p = data.new_password.strip()
        if len(new_p) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yangi parol kamida 6 ta belgidan iborat bo'lishi kerak."
            )
        current_user.hashed_password = hash_password(new_p)

    # 4. Majburiy o'zgartirish holatini bekor qilish
    current_user.must_change_password = False

    await db.commit()
    await db.refresh(current_user)

    # Yangi token generatsiya qilish
    expire_minutes = settings.STAFF_TOKEN_EXPIRE_MINUTES
    new_token = create_access_token(
        data={"sub": str(current_user.id), "role": current_user.role.value},
        expires_delta=None
    )

    return {
        "status": "success",
        "message": "Login va parol muvaffaqiyatli yangilandi.",
        "username": current_user.username,
        "access_token": new_token,
        "must_change_password": False
    }
