from typing import Dict, List, Any

# Tizimdagi barcha atomik huquqlar (Permissions Catalog)
PERMISSIONS_CATALOG: List[Dict[str, Any]] = [
    # 1. Murojaatlar moduli (appeals)
    {
        "code": "appeals:view_all",
        "name": "Barcha murojaatlarni ko'rish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Barcha bo'lim va xodimlarga tegishli arizalarni monitoring qilish"
    },
    {
        "code": "appeals:view_assigned",
        "name": "O'ziga biriktirilgan murojaatlarni ko'rish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Faqat xodimning o'ziga biriktirilgan arizalarni ko'rish"
    },
    {
        "code": "appeals:assign",
        "name": "Murojaatni ijrochiga biriktirish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Arizani tegishli bo'lim yoki mutaxassisga yo'naltirish"
    },
    {
        "code": "appeals:resolve",
        "name": "Murojaatni yakunlash va javob berish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Ariza ijrosini bajarish va rasmiy javob yuklash"
    },
    {
        "code": "appeals:reject",
        "name": "Murojaatni asosli rad etish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Asossiz yoki noto'g'ri berilgan arizalarni rad etish"
    },
    {
        "code": "appeals:prorektor_decision",
        "name": "Prorektor qarorini qabul qilish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "E'tirozli va eskalatsiya bo'lgan arizalar bo'yicha rahbariyat qarorini chiqarish"
    },
    {
        "code": "appeals:export",
        "name": "Murojaatlarni Excelga eksport qilish",
        "category": "appeals",
        "category_name": "Murojaatlar boshqaruvi",
        "description": "Reestrni formatlangan .xls faylida yuklab olish"
    },

    # 2. Darcha va Navbat moduli (queue)
    {
        "code": "queue:call",
        "name": "Navbatdagi talabani chaqirish",
        "category": "queue",
        "category_name": "Darcha va Elektron Navbat",
        "description": "O'z darchasiga navbatdagi qabul chiptasini chaqirish"
    },
    {
        "code": "queue:complete",
        "name": "Darcha qabulini yakunlash",
        "category": "queue",
        "category_name": "Darcha va Elektron Navbat",
        "description": "Mijozga xizmat ko'rsatish jarayonini yakunlash va baholatish"
    },
    {
        "code": "queue:manage_windows",
        "name": "Darchalar ish rejimini boshqarish",
        "category": "queue",
        "category_name": "Darcha va Elektron Navbat",
        "description": "Darchalarni ochish, yopish va tanaffus rejimlarini o'rnatish"
    },
    {
        "code": "queue:view_board",
        "name": "Umumiy navbat tablosini ko'rish",
        "category": "queue",
        "category_name": "Darcha va Elektron Navbat",
        "description": "Katta zal tablosini kuzatish"
    },

    # 3. Xizmatlar va Reglamentlar (services)
    {
        "code": "services:view",
        "name": "Xizmatlar katalogini ko'rish",
        "category": "services",
        "category_name": "Xizmatlar va Reglamentlar",
        "description": "Barcha rasmiy xizmatlar va bo'limlar ro'yxatini ko'rish"
    },
    {
        "code": "services:manage",
        "name": "Xizmatlar katalogini tahrirlash",
        "category": "services",
        "category_name": "Xizmatlar va Reglamentlar",
        "description": "Yangi xizmat qo'shish, SLA ijro vaqti va KPI ballarini o'zgartirish"
    },
    {
        "code": "services:delete",
        "name": "Xizmatlarni o'chirish / nofaol qilish",
        "category": "services",
        "category_name": "Xizmatlar va Reglamentlar",
        "description": "Xizmatlarni arxivlash va faolsizlantirish"
    },

    # 4. Foydalanuvchilar va Xodimlar (users)
    {
        "code": "users:view",
        "name": "Xodimlar ro'yxatini ko'rish",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "Tizimdagi barcha xodimlar va ularning biriktirilgan vazifalarini ko'rish"
    },
    {
        "code": "users:create",
        "name": "Yangi xodim qo'shish",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "Xodimlarni ro'yxatdan o'tkazish va bir martalik OTP parol yaratish"
    },
    {
        "code": "users:edit",
        "name": "Xodim ma'lumotlarini tahrirlash",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "F.I.SH., lavozim, bo'lim va aloqa ma'lumotlarini o'zgartirish"
    },
    {
        "code": "users:delete",
        "name": "Xodimni tizimdan o'chirish",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "Xodim hisobini butkul o'chirish yoki nofaol qilish"
    },
    {
        "code": "users:assign_services",
        "name": "Xodimga xizmatlarni biriktirish",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "Xodim ijro etadigan aniq xizmatlar ro'yxatini belgilash"
    },
    {
        "code": "roles:manage",
        "name": "Rollar va Huquqlar Matritsasini boshqarish",
        "category": "users",
        "category_name": "Xodimlar va Foydalanuvchilar",
        "description": "Yangi rollar yaratish va ularga ruxsatlar matritsasini belgilash"
    },

    # 5. Xavfsizlik va Audit jurnali (audit)
    {
        "code": "audit:view",
        "name": "Audit va xavfsizlik jurnalini ko'rish",
        "category": "audit",
        "category_name": "Xavfsizlik va Audit",
        "description": "Tizim tranzaksiyalari, kirishlar va o'zgarishlar jurnalini kuzatish"
    },
    {
        "code": "audit:export",
        "name": "Audit jurnalini Excelga yuklash",
        "category": "audit",
        "category_name": "Xavfsizlik va Audit",
        "description": "Audit yozuvlarini rasmiy hisobot sifatida yuklab olish"
    },

    # 6. Rahbariyat tahlili (analytics)
    {
        "code": "analytics:view",
        "name": "Tahliliy infografikalarni ko'rish",
        "category": "analytics",
        "category_name": "Rahbariyat Tahliliy Hisoboti",
        "description": "Murojaatlar, xizmatlar, fakultetlar va SLA statistikalarini tahlil qilish"
    },
    {
        "code": "analytics:export",
        "name": "Tahliliy hisobotni Excelga yuklash",
        "category": "analytics",
        "category_name": "Rahbariyat Tahliliy Hisoboti",
        "description": "Universitet rahbariyati uchun yig'ma hisobotni yuklab olish"
    },

    # 7. Tizim va Zaxiralar (system)
    {
        "code": "system:metrics",
        "name": "Server va tizim salomatligini kuzatish",
        "category": "system",
        "category_name": "Tizim va Zaxiralar",
        "description": "CPU, RAM, Disk va DB yuklamasi holatini ko'rish"
    },
    {
        "code": "system:backups_manage",
        "name": "Zaxira nusxalarini yaratish va yuklab olish",
        "category": "system",
        "category_name": "Tizim va Zaxiralar",
        "description": "Baza va fayllarning arxiv zaxirasini olish hamda yuklab olish"
    },
    {
        "code": "system:integrations",
        "name": "Telegram bot va HEMIS sozlamalarini boshqarish",
        "category": "system",
        "category_name": "Tizim va Zaxiralar",
        "description": "Shifrlangan bot tokeni va integratsiya parametrlarini sozlash"
    },

    # 8. E'lonlar markazi (announcements)
    {
        "code": "announcements:publish",
        "name": "Yangi e'lon va xabarnoma chiqarish",
        "category": "announcements",
        "category_name": "E'lonlar Markazi",
        "description": "Talabalar va xodimlar uchun rasmiy e'lonlar e'lon qilish"
    },
    {
        "code": "announcements:view_stats",
        "name": "E'lon statistikasi va o'qimaganlar ro'yxati",
        "category": "announcements",
        "category_name": "E'lonlar Markazi",
        "description": "E'lon bilan tanishganlar va tanishmaganlar ro'yxatini ko'rish hamda Excelga olish"
    }
]

ALL_PERMISSION_CODES = [p["code"] for p in PERMISSIONS_CATALOG]

# Dastlabki 6 ta shablon rollar (Default Template Roles)
DEFAULT_TEMPLATE_ROLES: List[Dict[str, Any]] = [
    {
        "code": "admin",
        "name": "Tizim Administratori",
        "description": "Barcha tizim funksiyalariga to'liq cheklovsiz daxlsiz huquq",
        "permissions": ["*"],
        "is_system": True,
        "is_immutable": True
    },
    {
        "code": "office_head",
        "name": "Registrator ofisi boshlig'i",
        "description": "Registrator ofisi faoliyati, xodimlar, arizalar va xizmatlar boshqaruvi",
        "permissions": [
            "appeals:view_all",
            "appeals:assign",
            "appeals:resolve",
            "appeals:reject",
            "appeals:export",
            "queue:view_board",
            "services:view",
            "services:manage",
            "users:view",
            "users:create",
            "users:edit",
            "users:delete",
            "users:assign_services",
            "audit:view",
            "audit:export",
            "analytics:view",
            "analytics:export",
            "announcements:publish",
            "announcements:view_stats"
        ],
        "is_system": True,
        "is_immutable": False
    },
    {
        "code": "vice_rector",
        "name": "O'quv ishlari bo'yicha prorektor",
        "description": "Rahbariyat qarorlari, eskalatsiya arizalari va tahliliy hisobotlar",
        "permissions": [
            "appeals:view_all",
            "appeals:prorektor_decision",
            "appeals:export",
            "analytics:view",
            "analytics:export",
            "announcements:view_stats"
        ],
        "is_system": True,
        "is_immutable": False
    },
    {
        "code": "front_staff",
        "name": "Front-ofis darcha xodimi",
        "description": "Talabalarni darchada bevosita qabul qilish va elektron navbatni yuritish",
        "permissions": [
            "queue:call",
            "queue:complete",
            "queue:view_board",
            "appeals:view_assigned",
            "appeals:resolve",
            "services:view"
        ],
        "is_system": True,
        "is_immutable": False
    },
    {
        "code": "back_staff",
        "name": "Back-ofis ijrochi xodim",
        "description": "Onlayn arizalarni ko'rib chiqish va rasmiy javob xatlarini tayyorlash",
        "permissions": [
            "appeals:view_assigned",
            "appeals:resolve",
            "services:view"
        ],
        "is_system": True,
        "is_immutable": False
    },
    {
        "code": "student",
        "name": "Talaba",
        "description": "Talabalar portali: ariza yuborish, navbat olish va natijalarni yuklab olish",
        "permissions": [],
        "is_system": True,
        "is_immutable": False
    }
]
