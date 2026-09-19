from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, hash_password, create_access_token, create_telegram_bind_token
from app.models import User, UserRole
from app.schemas import (
    UserLogin, HemisStudentLogin, TokenResponse, HemisTokenResponse,
    HemisRefreshRequest, UserOut, TelegramConnectInfo
)
from app.services.hemis_client import HemisClient
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])


@router.post("/login", response_model=TokenResponse, summary="Talaba va xodimlar uchun yagona kirish darchasi")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Yagona autentifikatsiya nuqtasi:
    - Registrator ofisi xodimlari, bo'lim boshlig'i, prorektor va administrator uchun;
    - HEMIS talabalari uchun (HEMIS API orqali tekshirish va profilni sinxronlashtirish).
    
    Foydalanuvchi roli avtomatik aniqlanadi va qaytariladi.
    """
    # 1. Mahalliy ma'lumotlar bazasidan tekshirish (xodimlar va mavjud talabalar)
    result = await db.execute(
        select(User).where(
            (User.username == credentials.username) | 
            (User.email == credentials.username) | 
            (User.hemis_student_id == credentials.username),
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if user and verify_password(credentials.password, user.hashed_password):
        expire_minutes = (
            settings.STUDENT_TOKEN_EXPIRE_MINUTES
            if user.role == UserRole.STUDENT
            else settings.STAFF_TOKEN_EXPIRE_MINUTES
        )
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=timedelta(minutes=expire_minutes)
        )
        await AuditService.log(
            db=db,
            entity_type="auth",
            entity_id=user.id,
            action="login",
            user_id=user.id,
            details=f"Tizimga muvaffaqiyatli kirdi: {user.full_name} ({user.role.value})"
        )
        await db.commit()
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            expires_in_minutes=expire_minutes,
            must_change_password=getattr(user, "must_change_password", False),
            hemis_token=user.hemis_refresh_token or "local-session-token",
            hemis_refresh_token=user.hemis_refresh_token
        )

    # 2. Agar mahalliy xodim bo'lmasa, real HEMIS orqali talabani tekshirish
    try:
        hemis_token_data = await HemisClient.login(credentials.username, credentials.password)
        access_token_remote = hemis_token_data["token"]
        refresh_token_remote = hemis_token_data.get("refresh_token")

        raw_profile = await HemisClient.get_me(access_token_remote)
        hemis_profile = HemisClient.filter_safe_academic_profile(raw_profile)

        student_id_str = hemis_profile["hemis_student_id"] or str(credentials.username)
        res_sync = await db.execute(
            select(User).where(
                (User.hemis_student_id == student_id_str) | (User.username == student_id_str)
            )
        )
        sync_user = res_sync.scalar_one_or_none()

        if sync_user:
            sync_user.full_name = hemis_profile["full_name"] or sync_user.full_name
            sync_user.faculty = hemis_profile["faculty"] or sync_user.faculty
            sync_user.group_name = hemis_profile["group_name"] or sync_user.group_name
            sync_user.course = hemis_profile["course"] or sync_user.course
            sync_user.specialty = hemis_profile["specialty"] or sync_user.specialty
            sync_user.education_type = hemis_profile["education_type"] or sync_user.education_type
            sync_user.education_form = hemis_profile["education_form"] or sync_user.education_form
            sync_user.email = hemis_profile["email"] or sync_user.email
            sync_user.phone = hemis_profile["phone"] or sync_user.phone
            sync_user.hemis_refresh_token = refresh_token_remote
            user_to_respond = sync_user
        else:
            new_student = User(
                username=student_id_str,
                hashed_password=hash_password(credentials.password),
                full_name=hemis_profile["full_name"],
                role=UserRole.STUDENT,
                hemis_student_id=student_id_str,
                faculty=hemis_profile["faculty"],
                group_name=hemis_profile["group_name"],
                course=hemis_profile["course"],
                specialty=hemis_profile["specialty"],
                education_type=hemis_profile["education_type"],
                education_form=hemis_profile["education_form"],
                email=hemis_profile["email"],
                phone=hemis_profile["phone"],
                hemis_refresh_token=refresh_token_remote
            )
            db.add(new_student)
            user_to_respond = new_student

        await db.commit()
        await db.refresh(user_to_respond)

        expire_minutes = settings.STUDENT_TOKEN_EXPIRE_MINUTES
        token = create_access_token(
            data={"sub": str(user_to_respond.id), "role": user_to_respond.role.value},
            expires_delta=timedelta(minutes=expire_minutes)
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            role=user_to_respond.role,
            user_id=user_to_respond.id,
            full_name=user_to_respond.full_name,
            expires_in_minutes=expire_minutes,
            hemis_token=access_token_remote,
            hemis_refresh_token=refresh_token_remote
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi nomi yoki parol noto'g'ri."
        )


@router.post("/hemis-login", response_model=HemisTokenResponse, summary="Talabalar uchun real HEMIS orqali kirish (2 kunlik sessiya)")
async def hemis_login(credentials: HemisStudentLogin, db: AsyncSession = Depends(get_db)):
    """
    Talabalar uchun https://student.jbnuu.uz/rest/v1/auth/login orqali kirish.
    Nizom va talabga binoan talaba sessiyasi 2 kun (2880 daqiqa) amal qiladi.
    
    SHAXSGA DOIR MAXFIYLIK QOIDASI (PII Protection):
    Tizim bazasida talabaning pasport ma'lumotlari (passport_pin) va manzili aslo saqlanmaydi!
    """
    hemis_token_data = None
    hemis_profile = None

    try:
        # 1. Real HEMIS API ga login so'rovi yuborish
        hemis_token_data = await HemisClient.login(credentials.hemis_login, credentials.password)
        access_token_remote = hemis_token_data["token"]
        refresh_token_remote = hemis_token_data.get("refresh_token")

        # 2. HEMIS orqali talaba ma'lumotlarini olish
        raw_profile = await HemisClient.get_me(access_token_remote)
        # 3. Shaxsiy pasport va manzil ma'lumotlarini qat'iy chetlatish
        hemis_profile = HemisClient.filter_safe_academic_profile(raw_profile)

    except HTTPException as http_exc:
        # Agar HEMIS 401 qaytarsa, aniq xatolikni uzatamiz
        if http_exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise http_exc

        # Agar HEMIS serveriga ulanib bo'lmasa (offline / test rejim), mahalliy bazadan tekshirish
        result = await db.execute(
            select(User).where(
                (User.hemis_student_id == str(credentials.hemis_login)) | (User.username == str(credentials.hemis_login)),
                User.is_active == True,
                User.role == UserRole.STUDENT
            )
        )
        local_user = result.scalar_one_or_none()
        if local_user and verify_password(credentials.password, local_user.hashed_password):
            expire_minutes = settings.STUDENT_TOKEN_EXPIRE_MINUTES
            token = create_access_token(
                data={"sub": str(local_user.id), "role": local_user.role.value},
                expires_delta=timedelta(minutes=expire_minutes)
            )
            return HemisTokenResponse(
                access_token=token,
                token_type="bearer",
                role=local_user.role,
                user_id=local_user.id,
                full_name=local_user.full_name,
                expires_in_minutes=expire_minutes,
                hemis_token="mock-hemis-token",
                hemis_refresh_token=local_user.hemis_refresh_token
            )
        raise http_exc

    # 4. Foydalanuvchini mahalliy bazada yangilash yoki yaratish (upsert)
    student_id_str = hemis_profile["hemis_student_id"] or str(credentials.hemis_login)
    result = await db.execute(
        select(User).where(
            (User.hemis_student_id == student_id_str) | (User.username == student_id_str)
        )
    )
    user = result.scalar_one_or_none()

    if user:
        # Mavjud talabaning akademik ma'lumotlarini yangilash
        user.full_name = hemis_profile["full_name"] or user.full_name
        user.faculty = hemis_profile["faculty"] or user.faculty
        user.group_name = hemis_profile["group_name"] or user.group_name
        user.course = hemis_profile["course"] or user.course
        user.specialty = hemis_profile["specialty"] or user.specialty
        user.education_type = hemis_profile["education_type"] or user.education_type
        user.education_form = hemis_profile["education_form"] or user.education_form
        user.email = hemis_profile["email"] or user.email
        user.phone = hemis_profile["phone"] or user.phone
        user.hemis_refresh_token = refresh_token_remote
    else:
        # Yangi talaba yaratish
        user = User(
            username=student_id_str,
            hashed_password=hash_password(credentials.password),
            full_name=hemis_profile["full_name"],
            role=UserRole.STUDENT,
            hemis_student_id=student_id_str,
            faculty=hemis_profile["faculty"],
            group_name=hemis_profile["group_name"],
            course=hemis_profile["course"],
            specialty=hemis_profile["specialty"],
            education_type=hemis_profile["education_type"],
            education_form=hemis_profile["education_form"],
            email=hemis_profile["email"],
            phone=hemis_profile["phone"],
            hemis_refresh_token=refresh_token_remote
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # 5. Tizimimizning 2 kunlik JWT tokenini generatsiya qilish
    expire_minutes = settings.STUDENT_TOKEN_EXPIRE_MINUTES
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=timedelta(minutes=expire_minutes)
    )

    return HemisTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        expires_in_minutes=expire_minutes,
        hemis_token=access_token_remote,
        hemis_refresh_token=refresh_token_remote
    )


@router.post("/hemis-refresh", summary="HEMIS sessiya tokenini X-Refresh-Token orqali yangilash")
async def hemis_refresh(data: HemisRefreshRequest):
    """
    HEMIS sessiyasini har safar login/parol kiritmasdan X-Refresh-Token orqali uzaytirish.
    """
    return await HemisClient.refresh_token(data.refresh_token)


@router.get("/me", response_model=UserOut, summary="Joriy foydalanuvchi profili")
async def get_me(current_user: User = Depends(get_current_user)):
    """Avtorizatsiyadan o'tgan foydalanuvchining shaxsiy ma'lumotlari."""
    return current_user


@router.get("/telegram-info", response_model=TelegramConnectInfo, summary="Telegram bot bog'lanish holati va havolasi")
async def get_telegram_info(current_user: User = Depends(get_current_user)):
    """Foydalanuvchining Telegram botga ulanganligi holati va bot havolasi."""
    bot_user = settings.TELEGRAM_BOT_USERNAME
    bind_token = create_telegram_bind_token(current_user.id)
    deep_link = f"https://t.me/{bot_user}?start=bind_{bind_token}"
    return TelegramConnectInfo(
        bot_username=bot_user,
        is_connected=bool(current_user.telegram_chat_id),
        telegram_chat_id=current_user.telegram_chat_id,
        telegram_username=current_user.telegram_username,
        deep_link=deep_link
    )
