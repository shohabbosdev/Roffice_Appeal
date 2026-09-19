import secrets
import string
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models import User, UserRole, Service
from app.schemas import (
    UserOut, UserRoleUpdate, StaffCreate, StaffCreateResponse,
    StaffUpdate, UpdateCredentialsRequest, ServiceOut, StaffServiceAssignRequest
)
from app.api.deps import require_role, get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["Foydalanuvchilar va rollar boshqaruvi"])


# Oliy ta'lim, fan va innovatsiyalar vazirligi 73-sonli buyrug'i (Namunaviy Nizom)
# bo'yicha rollar va sektorlar kesimidagi to'liq rasmiy xizmat vazifalari katalogi
NIZOM_DUTIES_CATALOG = [
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Talabalarga xizmat ko'rsatish va ma'lumotnomalar berish sektori (1-darcha)",
        "duties": [
            "O'qish joyidan QR-kodli elektron ma'lumotnoma shakllantirish va berish",
            "Transkript (baholar ko'chirmasi) va akademik ko'chirmalarni taqdim etish",
            "Sirtqi va masofaviy ta'lim shakli talabalari uchun chaqiruv qog'ozlarini shakllantirish",
            "Talabaga shaxsiy GPA ko'rsatkichi haqida ma'lumotnoma berish",
            "Talabalarning HEMIS axborot tizimidagi parolini tiklash",
            "Talaba guvohnomasi va turar joyi guvohnomasini yaratish hamda taqdim etish",
            "Dars jadvallari, oraliq va yakuniy nazoratlar jadvali bo'yicha konsultatsiya berish",
            "Qayta o'qish uchun fan guruhlariga ariza topshirishda talabaga yordam ko'rsatish",
            "Talabalar turar joyiga ko'chib o'tganlarni vaqtinchalik ro'yxatga qo'yish hujjatlarini tayyorlash",
            "Darcha qabulida 15 daqiqalik elektron navbat taloni bo'yicha bevosita xizmat ko'rsatish"
        ]
    },
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Buxgalteriya va marketing sektori (2-darcha)",
        "duties": [
            "To'lov-kontrakt shartnoma summasini aniqlash, hisoblash va shartnomalarni taqdim etish",
            "Talabalar stipendiyasi va moddiy yordam arizalarini birlamchi qabul qilish",
            "HEMIS platformasi natijalari asosida stipendiya tayinlash buyruqlari loyihalarini tayyorlash",
            "Akademik qarzdor talabalar uchun qayta o'zlashtirish to'lov miqdorlarini hisoblash va shartnoma berish",
            "Ijara to'lovi subsidiyasi olish uchun arizalarni qabul qilish va ekspertiza qilish",
            "Talabalarning yotoqxonalarga joylashishi uchun arizalarini ro'yxatga olish",
            "Bitiruvchilarni ishga taqsimlash, ishga yuborilganlik yo'llanmasi va shaxsiy taqsimot qaydnomasini rasmiylashtirish",
            "Potensial ish beruvchilar bazasini shakllantirish va talabalarga yetkazish"
        ]
    },
    {
        "role": UserRole.FRONT_STAFF.value,
        "sector": "Ilmiy-innovatsion faoliyat va xalqaro aloqalar sektori (3-darcha)",
        "duties": [
            "O'qish joyidan ingliz tilida rasmiy ma'lumotnomalar berish",
            "Xalqaro grantlar, akademik mobillik dasturlari va 'El-yurt umidi' jamg'armasi stipendiyalari bo'yicha konsultatsiya",
            "O'qishga qabul qilingan xorijlik talabalarni elektron tizimda ro'yxatga olish va fanlarga biriktirish",
            "Xorijlik talabalar uchun viza rasmiylashtirish va O'zbekiston Respublikasida vaqtinchalik ro'yxatga qo'yish",
            "Nomdor davlat stipendiyalari, ilmiy konferensiyalar va startap tanlovlariga talabalar arizalarini qabul qilish",
            "Qo'shma ta'lim dasturlari bo'yicha talabalarga ma'lumot berish va targ'ibot qilish",
            "'Ustoz-shogird' maktabi va ilmiy to'garaklar faoliyatini muvofiqlashtirish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "Statistik ma'lumotlarni yuritish va tahlil sektori",
        "duties": [
            "Talabalar soni, resurslar, to'lov-shartnomalar va o'zlashtirish bo'yicha tahliliy ma'lumotlar bankini yuritish",
            "Kursdan kursga qolgan, safdan chetlashtirilgan va akademik ta'tildagi talabalar statistikasini shakllantirish",
            "O'qishni ko'chirish va tiklashga tavsiya etilgan talabalar bo'yicha umumiy statistik hisobotlar tayyorlash",
            "O'zbekiston Respublikasi Statistika agentligi va vazirlikka taqdim etiladigan rasmiy hisobot shakllarini yuritish",
            "Bitiruvchilar umumiy ma'lumotlar bankini shakllantirish va bandlik monitoringini olib borish",
            "HEMIS axborot tizimiga kiritilayotgan statistik ko'rsatkichlarning to'g'riligini doimiy audit qilish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "O'quv jarayonini muvofiqlashtirish sektori",
        "duties": [
            "Akademik guruhlarni shakllantirish va talabalarni guruhlarga kiritish",
            "Qayta o'qish fan guruhlari, dars jadvallari va nazorat grafiklarini tizimda yaratish",
            "Talabalarni tegishli tanlov fanlariga hamda tyutorlarga biriktirish",
            "O'quv rejada mavjud fanlarni semestrlarga taqsimlash va yuklamalarni nazorat qilish",
            "Talabalar harakati buyruqlari (chetlashtirish, tiklash, ko'chirish, akademik ta'til) loyihalarini rasmiylashtirish",
            "Talabalarni kursdan kursga o'tkazish buyruqlarini tizim orqali tayyorlash",
            "HEMIS tizimi orqali talabalar davomatini monitoring qilish va kunlik hisobotlarni shakllantirish",
            "Yakuniy nazoratlar jadvalini tizimga joylashtirish va o'tkazilishini nazorat qilish"
        ]
    },
    {
        "role": UserRole.BACK_STAFF.value,
        "sector": "Talabalar hujjatlarini yuritish va saqlash (Arxiv) sektori",
        "duties": [
            "O'qishni tugatgan talabalar shaxsiy yig'majildlarini to'plash, tikish va arxivga topshirish",
            "Familiyasi o'zgargan, akademik ta'tilga chiqqan, yo'nalishini o'zgartirgan talabalarning buyruq ko'chirmalarini bazaga joylash",
            "Qat'iy hisobdagi hujjatlar va blankalar (diplom, diplom ilovasi, akademik sertifikatlar) hisobini yuritish, saqlash va berish",
            "Akademik qarzdor talabalar ro'yxatini aniqlash va xabarnomalar tayyorlash",
            "Diplomlarning haqiqiyligini tekshirish (d-arxiv.edu.uz va mehnat.uz platformalari orqali tashkilotlar so'rovlariga javob berish)",
            "Yo'qotilgan diplom va ilovalar o'rniga dublikat berish to'g'risidagi arizalarni ekspertiza qilish va javob qaytarish"
        ]
    },
    {
        "role": UserRole.OFFICE_HEAD.value,
        "sector": "Registrator ofisi rahbariyati",
        "duties": [
            "Registrator ofisi faoliyatini umumiy boshqarish, xodimlar o'rtasida xizmat vazifalarini taqsimlash va muvofiqlashtirish",
            "Front va Back office bo'lim boshliqlari hamda menejerlar faoliyatini doimiy monitoring qilish",
            "Murojaatlarning SLA ijro muddatlari va elektron navbat sifatini real vaqt rejimida nazorat qilish",
            "Xodimlarning oylik KPI (150 ballik reja) ko'rsatkichlarini audit qilish, tasdiqlash va rag'batlantirish takliflarini kiritish",
            "2-bosqich ichki nizolar (dispute): talaba e'tiroz bildirgan arizalarni bevosita ko'rib chiqish va hal etish",
            "Yechilmagan murakkab nizoli masalalarni O'quv ishlari bo'yicha prorektorga (3-bosqich) eskalatsiya qilish",
            "Ofis tomonidan ko'rsatiladigan xizmatlar turlarini kengaytirish va sifatini oshirish strategiyalarini ishlab chiqish"
        ]
    },
    {
        "role": UserRole.VICE_RECTOR.value,
        "sector": "O'quv ishlari bo'yicha prorektorat",
        "duties": [
            "Ofis faoliyati ustidan oliy nazoratni amalga oshirish va umumiy metodik rahbarlik qilish",
            "Eskalatsiya qilingan bahsli akademik murojaatlar bo'yicha yakuniy va majburiy qaror qabul qilish",
            "Filial Talabalar apellyatsiya komissiyasi faoliyatiga rahbarlik qilish",
            "O'quv jarayoni grafigi va yakuniy nazoratlar o'tkazish jadvallarini tasdiqlash",
            "Registrator ofisi xodimlarining shtat birliklari va lavozim yo'riqnomalarini muvofiqlashtirish"
        ]
    },
    {
        "role": UserRole.STUDENT.value,
        "sector": "Filial talabalari (Foydalanuvchilar)",
        "duties": [
            "HEMIS yagona autentifikatsiyasi orqali tizimga kirish va akademik profilini tekshirish",
            "Reglament bo'yicha ruxsat etilgan ta'lim shakllarida (sirtqi, masofaviy) onlayn murojaat yo'llash",
            "Registrator ofisiga shaxsan tashrif buyurish uchun 'Kelib hal etish' bo'yicha elektron navbat taloni olish",
            "Olingan navbat taloni bilan ofisga (104-xona) belgilangan vaqt oralig'ida tashrif buyurish va Check-in qilish",
            "Tayyorlangan rasmiy ijro natijasi va ma'lumotnomalarni yuklab olish",
            "Ijro etilgan arizalarni 1 dan 5 gacha baholash yoki asoslantirilgan e'tiroz (dispute) bildirish",
            "Telegram bot orqali arizalar holati va elektron talon xabarnomalarini qabul qilish"
        ]
    },
    {
        "role": UserRole.ADMIN.value,
        "sector": "Tizim ma'muriyati va AKT sektori",
        "duties": [
            "Foydalanuvchilar hisoblarini yaratish, rollarni biriktirish, vaqtinchalik parollarni boshqarish",
            "Registrator ofisi sohalari/bo'limlari va xizmat ko'rsatish darchalarini konfiguratsiya qilish",
            "Xizmatlar katalogi, xizmatlarning KPI ballari va SLA soatlarini sozlash",
            "Ta'lim shakllari (kunduzgi, sirtqi, masofaviy) onlayn murojaat cheklov siyosatini boshqarish",
            "Ish vaqti, rasmiy bayramlar va dam olish kunlari kalendarini yangilab borish",
            "HEMIS API va Telegram Bot integratsiyasi texnik barqarorligini ta'minlash",
            "Tizim xavfsizlik auditi, ma'lumotlar bazasi zaxira nusxalarini yaratish va nazorat qilish"
        ]
    }
]


@router.get("/nizom-duties", summary="Registrator ofisi nizomi bo'yicha xizmat vazifalari katalogi")
async def get_nizom_duties(current_user: User = Depends(get_current_user)):
    """Nizomda belgilangan barcha sohalar va xizmat vazifalari ro'yxati."""
    return NIZOM_DUTIES_CATALOG


@router.get("/me", response_model=UserOut, summary="Joriy foydalanuvchi profili")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Joriy avtorizatsiyadan o'tgan foydalanuvchining shaxsiy ma'lumotlari."""
    return current_user


@router.get("/staff", response_model=List[UserOut], summary="Barcha xodimlar va ularning joriy rollari ro'yxati")
async def get_staff_list(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD, UserRole.VICE_RECTOR)),
    db: AsyncSession = Depends(get_db)
):
    """Admin yoki Boshliq uchun barcha xodimlarni ko'rish va boshqarish ro'yxati."""
    query = (
        select(User)
        .options(selectinload(User.department), selectinload(User.assigned_services))
        .where(User.role != UserRole.STUDENT)
        .order_by(User.id.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserOut, summary="Bitta xodimning to'liq ma'lumotlari")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(User)
        .options(selectinload(User.department), selectinload(User.assigned_services))
        .where(User.id == user_id)
    )
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return user


@router.get("/{user_id}/services", response_model=List[ServiceOut], summary="Xodimga biriktirilgan xizmatlar ro'yxati")
async def get_staff_services(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD, UserRole.FRONT_STAFF, UserRole.BACK_STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Xodimga biriktirilgan xizmatlar katalogi."""
    query = (
        select(User)
        .options(selectinload(User.assigned_services).selectinload(Service.department))
        .where(User.id == user_id)
    )
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")
    return user.assigned_services


@router.put("/{user_id}/services", response_model=List[ServiceOut], summary="Xodimga xizmatlarni biriktirish (Admin / Boshliq)")
async def assign_staff_services(
    user_id: int,
    data: StaffServiceAssignRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OFFICE_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """Xodimga bitta yoki bir nechta xizmatlarni dinamik biriktirish."""
    query = (
        select(User)
        .options(selectinload(User.assigned_services))
        .where(User.id == user_id)
    )
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    if data.service_ids:
        services_query = (
            select(Service)
            .options(selectinload(Service.department))
            .where(Service.id.in_(data.service_ids), Service.is_active == True)
        )
        services = (await db.execute(services_query)).scalars().all()
        user.assigned_services = list(services)
    else:
        user.assigned_services = []

    await db.commit()

    query = (
        select(User)
        .options(selectinload(User.assigned_services).selectinload(Service.department))
        .where(User.id == user_id)
    )
    reloaded = (await db.execute(query)).scalar_one()
    return reloaded.assigned_services


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

    # 8-character secure alphanumeric OTP generation or admin-provided custom password (min 6 chars)
    if data.custom_password and len(data.custom_password.strip()) >= 6:
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

    if data.service_ids:
        services_res = await db.execute(
            select(Service).where(Service.id.in_(data.service_ids), Service.is_active == True)
        )
        new_staff.assigned_services = list(services_res.scalars().all())

    db.add(new_staff)
    await db.commit()

    await AuditService.log(
        db=db,
        entity_type="staff",
        entity_id=new_staff.id,
        action="staff_created",
        user_id=current_user.id,
        details=f"Yangi xodim qo'shildi: {new_staff.full_name} ({new_staff.role.value})"
    )

    query = (
        select(User)
        .options(selectinload(User.department), selectinload(User.assigned_services))
        .where(User.id == new_staff.id)
    )
    reloaded_user = (await db.execute(query)).scalar_one()

    return StaffCreateResponse(
        user=reloaded_user,
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
    query = (
        select(User)
        .options(selectinload(User.department), selectinload(User.assigned_services))
        .where(User.id == user_id)
    )
    user = (await db.execute(query)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi.")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.username is not None and data.username.strip():
        new_u = data.username.strip()
        if new_u != user.username:
            existing = await db.execute(select(User).where(User.username == new_u))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ushbu login band.")
            user.username = new_u
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

    if data.service_ids is not None:
        if data.service_ids:
            services_res = await db.execute(
                select(Service).where(Service.id.in_(data.service_ids), Service.is_active == True)
            )
            user.assigned_services = list(services_res.scalars().all())
        else:
            user.assigned_services = []

    # Agar admin xodimga yangi parol belgilasa
    if data.new_password and len(data.new_password.strip()) >= 6:
        user.hashed_password = hash_password(data.new_password.strip())
        user.must_change_password = False
    elif data.reset_password:
        chars = string.ascii_letters + string.digits
        new_otp = "".join(secrets.choice(chars) for _ in range(8))
        user.hashed_password = hash_password(new_otp)
        user.must_change_password = True

    await db.commit()

    query = (
        select(User)
        .options(selectinload(User.department), selectinload(User.assigned_services))
        .where(User.id == user.id)
    )
    return (await db.execute(query)).scalar_one()


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

    await AuditService.log(
        db=db,
        entity_type="staff",
        entity_id=user.id,
        action="role_updated",
        user_id=current_user.id,
        details=f"Xodim roli yangilandi: {user.full_name} -> {data.role.value}"
    )

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

    await AuditService.log(
        db=db,
        entity_type="auth",
        entity_id=current_user.id,
        action="credentials_updated",
        user_id=current_user.id,
        details=f"Hisob ma'lumotlari yangilandi: {current_user.username}"
    )

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
