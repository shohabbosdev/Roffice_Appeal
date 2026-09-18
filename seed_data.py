import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import hash_password
from app.models import (
    User, UserRole, Department, DepartmentType, Service, ResolutionMode,
    EmployeeKPITarget, Holiday
)
from app.core.config import settings


async def seed_database():
    print("Baza jadvallarini yaratish va dastlabki ma'lumotlarni kiritish boshlandi...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_admin = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalar_one_or_none()

        if existing_admin:
            print("Dastlabki ma'lumotlar allaqachon kiritilgan!")
            return

        # 1. Registrator ofisi bo'limlari (Nizomga muvofiq)
        dept_front1 = Department(
            name="Talabalarga xizmat ko'rsatish va ma'lumotnomalar berish sektori",
            code="FRONT_STUDENT_SVC",
            dept_type=DepartmentType.FRONT_OFFICE,
            window_number="1-darcha"
        )
        dept_front2 = Department(
            name="Shartnoma, to'lovlar va stipendiya masalalari sektori",
            code="FRONT_FINANCE",
            dept_type=DepartmentType.FRONT_OFFICE,
            window_number="2-darcha"
        )
        dept_front3 = Department(
            name="Maslahat, qabul va umumiy arizalar sektori",
            code="FRONT_CONSULTING",
            dept_type=DepartmentType.FRONT_OFFICE,
            window_number="3-darcha"
        )
        dept_back1 = Department(
            name="O'quv jarayonini tahlil qilish va nazorat sektori",
            code="BACK_ACADEMIC_ANALYSIS",
            dept_type=DepartmentType.BACK_OFFICE,
            window_number=None
        )
        dept_back2 = Department(
            name="Hujjatlar aylanishi va arxiv sektori",
            code="BACK_ARCHIVE",
            dept_type=DepartmentType.BACK_OFFICE,
            window_number=None
        )
        dept_back3 = Department(
            name="Reyting va akademik ko'rsatkichlar sektori",
            code="BACK_GRADING",
            dept_type=DepartmentType.BACK_OFFICE,
            window_number=None
        )
        dept_back4 = Department(
            name="HEMIS tizimi va AKT integratsiyasi sektori",
            code="BACK_IT_HEMIS",
            dept_type=DepartmentType.BACK_OFFICE,
            window_number=None
        )

        departments = [
            dept_front1, dept_front2, dept_front3,
            dept_back1, dept_back2, dept_back3, dept_back4
        ]
        session.add_all(departments)
        await session.flush()

        # 2. Xizmatlar katalogi (Vazirlik 73-sonli buyrug'i va Nizom IV-bo'lim)
        services = [
            # Front Office - 1-darcha
            Service(
                department_id=dept_front1.id,
                code="SVC-FRONT-001",
                title="Talabalik to'g'risida ma'lumotnoma berish",
                description="O'qish joyidan talabalik faktini tasdiqlovchi QR-kodli elektron ma'lumotnoma",
                kpi_points=2,
                sla_hours=2,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Talaba ID raqami"
            ),
            Service(
                department_id=dept_front1.id,
                code="SVC-FRONT-002",
                title="Transkript (Baholar ko'chirmasi) berish",
                description="O'zlashtirilgan fanlar va to'plangan kreditlar ko'rsatilgan rasmiy transkript",
                kpi_points=4,
                sla_hours=24,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Elektron ariza"
            ),
            Service(
                department_id=dept_front1.id,
                code="SVC-FRONT-003",
                title="Talabalik guvohnomasini qayta tiklash",
                description="Yo'qolgan yoki yaroqsiz holga kelgan talabalik guvohnomasini tiklash",
                kpi_points=5,
                sla_hours=48,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Topilmalar byurosi ma'lumotnomasi, 3x4 rasm"
            ),
            Service(
                department_id=dept_front1.id,
                code="SVC-FRONT-004",
                title="Diplom dublikati olish uchun murojaat",
                description="Yo'qolgan yoki shikastlangan oliy ma'lumot to'g'risidagi diplom dublikatini rasmiylashtirish",
                kpi_points=7,
                sla_hours=72,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Gazeta e'loni, ariza, pasport nusxasi"
            ),

            # Front Office - 2-darcha (Moliyaviy)
            Service(
                department_id=dept_front2.id,
                code="SVC-FRONT-005",
                title="Kontrakt to'lovi hisob-fakturasini shakllantirish",
                description="To'lov-shartnoma hisob varag'ini olish va rekvizitlarni yangilash",
                kpi_points=3,
                sla_hours=2,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Shartnoma raqami"
            ),
            Service(
                department_id=dept_front2.id,
                code="SVC-FRONT-006",
                title="Shartnoma to'lovini bo'lib to'lash to'g'risida ariza",
                description="Kontrakt summasini reja-grafik asosida bo'lib to'lashga ruxsat olish",
                kpi_points=4,
                sla_hours=24,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Asoslantiruvchi hujjatlar, ariza"
            ),
            Service(
                department_id=dept_front2.id,
                code="SVC-FRONT-007",
                title="Imtiyozli stipendiya yoki moddiy yordam arizasi",
                description="Ijtimoiy himoyaga muhtoj talabalar uchun komissiya ko'rib chiqishiga yo'llash",
                kpi_points=5,
                sla_hours=72,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Mahalla ma'lumotnomasi, ijtimoiy reestr hujjati"
            ),

            # Front Office - 3-darcha (Konsultatsiya / Perevod / Qabul)
            Service(
                department_id=dept_front3.id,
                code="SVC-FRONT-008",
                title="O'qishni ko'chirish (Perevod) arizasini rasmiylashtirish",
                description="Boshqa OTMdan yoki ta'lim yo'nalishidan ko'chirish arizasini qabul qilish",
                kpi_points=8,
                sla_hours=72,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Transkript, reyting daftarchasi nusxasi, ariza"
            ),
            Service(
                department_id=dept_front3.id,
                code="SVC-FRONT-009",
                title="Akademik ta'tildan qaytish arizasi",
                description="Akademik ta'til muddati tugagach o'qish jarayonini davom ettirish",
                kpi_points=6,
                sla_hours=48,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Tibbiy xulosa (agar kasallik sababli bo'lsa), shaxsiy ariza"
            ),
            Service(
                department_id=dept_front3.id,
                code="SVC-FRONT-010",
                title="Kreditlarni qayta topshirish (Qayta o'qish) arizasi",
                description="Akademik qarzdorlikni yopish uchun fanlarni qayta o'zlashtirish",
                kpi_points=6,
                sla_hours=48,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Ariza, kredit to'lovi cheki"
            ),

            # Back Office - IT va HEMIS
            Service(
                department_id=dept_back4.id,
                code="SVC-BACK-011",
                title="HEMIS tizimidagi fan tanlovini tasdiqlash yoki xatolikni tuzatish",
                description="Elektron tizimdagi o'quv dasturi, guruh yoki fan tanlashdagi nomuvofiqlikni bartaraf etish",
                kpi_points=5,
                sla_hours=24,
                resolution_mode=ResolutionMode.ONLINE_ONLY,
                required_docs="Skrinshot va talaba logini"
            ),

            # Back Office - Reyting va Baholash
            Service(
                department_id=dept_back3.id,
                code="SVC-BACK-012",
                title="Reyting qaydnomasi (Vedomost) bo'yicha apellatsiya",
                description="Oraliq yoki yakuniy nazorat baholari tizimda noto'g'ri qayd etilganligi bo'yicha tekshiruv",
                kpi_points=8,
                sla_hours=72,
                resolution_mode=ResolutionMode.ONLINE_ONLY,
                required_docs="Apellatsiya arizasi, yozma ish fotosurati"
            ),
            Service(
                department_id=dept_back3.id,
                code="SVC-BACK-013",
                title="GPA ko'rsatkichi va qarz fanlarni qayta hisoblash",
                description="Kredit-modul tizimida GPA balli va fanlar sonini audit qilish",
                kpi_points=7,
                sla_hours=48,
                resolution_mode=ResolutionMode.ONLINE_ONLY,
                required_docs="Ariza"
            ),

            # Back Office - Arxiv
            Service(
                department_id=dept_back2.id,
                code="SVC-BACK-014",
                title="Arxivdan o'quv reja yoki dastur ko'chirmasini olish",
                description="Xorijiy OTMlarga o'qishni ko'chirish yoki ishga kirish uchun arxiv hujjatlari",
                kpi_points=7,
                sla_hours=72,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Shaxsni tasdiqlovchi hujjat"
            ),

            # Back Office - O'quv jarayoni
            Service(
                department_id=dept_back1.id,
                code="SVC-BACK-015",
                title="Chetlatilgan talabani o'qishga qayta tiklash",
                description="OTMdan chetlashtirilgan talabaning o'qishini tiklash buyrug'ini tayyorlash",
                kpi_points=9,
                sla_hours=120,
                resolution_mode=ResolutionMode.BOTH,
                required_docs="Ariza, akademik ma'lumotnoma, to'lov hujjati"
            )
        ]
        session.add_all(services)
        await session.flush()

        # 3. Foydalanuvchilar (Rahbariyat, Xodimlar, Talabalar)
        # Rahbariyat
        user_admin = User(
            username="admin",
            email="admin@jbnuu.uz",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Tizim Ma'muri",
            role=UserRole.ADMIN
        )
        user_head = User(
            username="akrom_head",
            email="a.vohidov@jbnuu.uz",
            hashed_password=hash_password("HeadPass123!"),
            full_name="Akrom Vohidov",
            role=UserRole.OFFICE_HEAD
        )
        user_prorektor = User(
            username="prorektor_edu",
            email="sh.rahimov@jbnuu.uz",
            hashed_password=hash_password("ProrektorPass123!"),
            full_name="Sherzod Rahimov",
            role=UserRole.VICE_RECTOR
        )

        # Xodimlar
        staff_malika = User(
            username="malika_front",
            email="m.karimova@jbnuu.uz",
            phone="+998901234567",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Malika Karimova",
            role=UserRole.FRONT_STAFF,
            department_id=dept_front1.id
        )
        staff_jasur = User(
            username="jasur_front",
            email="j.toshmatov@jbnuu.uz",
            phone="+998912345678",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Jasur Toshmatov",
            role=UserRole.FRONT_STAFF,
            department_id=dept_front2.id
        )
        staff_anvar = User(
            username="anvar_back",
            email="a.qodirov@jbnuu.uz",
            phone="+998933456789",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Anvar Qodirov",
            role=UserRole.BACK_STAFF,
            department_id=dept_back1.id
        )
        staff_nodira = User(
            username="nodira_back",
            email="n.saidova@jbnuu.uz",
            phone="+998944567890",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Nodira Saidova",
            role=UserRole.BACK_STAFF,
            department_id=dept_back3.id
        )

        # Talabalar
        student_azamat = User(
            username="student_azamat",
            email="azamat.r@student.jbnuu.uz",
            phone="+998977654321",
            hashed_password=hash_password("StudentPass123!"),
            full_name="Azamat Rustamov",
            role=UserRole.STUDENT,
            hemis_student_id="HEMIS-2024-101",
            faculty="Axborot texnologiyalari",
            course=3,
            education_type="Bakalavr",
            specialty="Dasturiy injiniring"
        )
        student_shahlo = User(
            username="student_shahlo",
            email="shahlo.r@student.jbnuu.uz",
            phone="+998988765432",
            hashed_password=hash_password("StudentPass123!"),
            full_name="Shahlo Rahimova",
            role=UserRole.STUDENT,
            hemis_student_id="HEMIS-2024-102",
            faculty="Iqtisodiyot",
            course=2,
            education_type="Bakalavr",
            specialty="Buxgalteriya hisobi va audit"
        )
        # Real HEMIS test student
        student_zoxidjon = User(
            username="401251200032",
            email="zokhidjonyuta@gmail.com",
            phone="+998772501326",
            hashed_password=hash_password("(Zetmax0011)"),
            full_name="QODIROV ZOXIDJON TOHIR O‘G‘LI",
            role=UserRole.STUDENT,
            hemis_student_id="401251200032",
            faculty="MAGISTRATURA",
            group_name="M07-25",
            course=2,
            education_type="Magistr",
            education_form="Kunduzgi",
            specialty="Dasturiy injiniring"
        )

        users = [
            user_admin, user_head, user_prorektor,
            staff_malika, staff_jasur, staff_anvar, staff_nodira,
            student_azamat, student_shahlo, student_zoxidjon
        ]
        session.add_all(users)
        await session.flush()

        # 4. Rasmiy bayramlar kalendari (2026-yil)
        holidays_2026 = [
            Holiday(holiday_date="2026-01-01", title="Yangi yil bayrami", is_working_day=False),
            Holiday(holiday_date="2026-03-08", title="Xalqaro xotin-qizlar kuni", is_working_day=False),
            Holiday(holiday_date="2026-03-21", title="Navro'z umumxalq bayrami", is_working_day=False),
            Holiday(holiday_date="2026-05-09", title="Xotira va qadrlash kuni", is_working_day=False),
            Holiday(holiday_date="2026-09-01", title="Mustaqillik kuni", is_working_day=False),
            Holiday(holiday_date="2026-10-01", title="O'qituvchi va murabbiylar kuni", is_working_day=False),
            Holiday(holiday_date="2026-12-08", title="Konstitutsiya kuni", is_working_day=False),
        ]
        session.add_all(holidays_2026)
        await session.flush()

        # 4. Xodimlar uchun joriy oylik KPI standart ko'rsatkichlari (150 ball)
        current_period = datetime.now(timezone.utc).strftime("%Y-%m")
        staff_list = [staff_malika, staff_jasur, staff_anvar, staff_nodira]
        for staff in staff_list:
            kpi_entry = EmployeeKPITarget(
                employee_id=staff.id,
                period=current_period,
                target_points=settings.DEFAULT_MONTHLY_KPI_TARGET,
                completed_points=0,
                penalty_points=0,
                total_appeals_completed=0,
                total_appointments_completed=0,
                average_rating=5.0,
                kpi_percentage=0.0
            )
            session.add(kpi_entry)

        await session.commit()
        print("Barcha ma'lumotlar muvaffaqiyatli saqlandi!")
        print(f"- Bo'limlar soni: {len(departments)}")
        print(f"- Xizmatlar soni: {len(services)}")
        print(f"- Foydalanuvchilar soni: {len(users)}")
        print(f"- Xodimlar KPI maqsadlari belgilandi ({current_period}, 150 ball)")


if __name__ == "__main__":
    asyncio.run(seed_database())
