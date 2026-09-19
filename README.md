# Registrator Ofisi — Murojaatlar, Elektron Navbat, Tahliliy Dashboard va Audit Tizimi

Mirzo Ulug'bek nomidagi O'zbekiston Milliy universiteti Jizzax filialining Registrator ofisi talabalar murojaatlari, "Kelib hal etish" elektron navbat tizimi, xodimlar KPI samaradorligini avtomatlashtirilgan baholash hamda Universitet rahbariyati uchun markazlashgan tahliliy nazorat platformasi.

> O'zbekiston Respublikasi Oliy ta'lim, fan va innovatsiyalar vazirligining 2025-yil 24-fevraldagi 73-sonli buyrug'i (Namunaviy Nizom) talablari asosida to'liq ishlab chiqilgan va amaliyotga tatbiq etilgan.

---

## Mundarija

1. [Loyiha Haqida](#1-loyiha-haqida)
2. [Texnologik Stek](#2-texnologik-stek)
3. [Tizim Arxitekturasi va Rollar (RBAC)](#3-tizim-arxitekturasi-va-rollar-rbac)
4. [Asosiy Modullar va Imkoniyatlar](#4-asosiy-modullar-va-imkoniyatlar)
   - [4.1. Talabalar Portali (`portal.html`)](#41-talabalar-portali-portalhtml)
   - [4.2. Xodimlar va Rahbariyat Ish Stoli (`staff.html`)](#42-xodimlar-va-rahbariyat-ish-stoli-staffhtml)
   - [4.3. Jonli Navbat Tablosi (`board.html` / `display.html`)](#43-jonli-navbat-tablosi-boardhtml--displayhtml)
   - [4.4. Rahbariyat Infografik Tahliliy Dashboardi](#44-rahbariyat-infografik-tahliliy-dashboardi)
   - [4.5. Real-Vaqt Audio va Jonli Indikatorlar (Live Badges)](#45-real-vaqt-audio-va-jonli-indikatorlar-live-badges)
   - [4.6. Telegram Bot va Foniy Eslatmalar Tizimi](#46-telegram-bot-va-foniy-eslatmalar-tizimi)
   - [4.7. Nizolarni 3 Bosqichli Eskalatsiya Qilish va Prorektor Qarori](#47-nizolarni-3-bosqichli-eskalatsiya-qilish-va-prorektor-qarori)
   - [4.8. Tizim Xavfsizligi va Markaziy Audit Jurnali](#48-tizim-xavfsizligi-va-markaziy-audit-jurnali)
5. [Biznes Mantiq, Formula va Algoritmlar](#5-biznes-mantiq-formula-va-algoritmlar)
   - [SLA Ish Vaqti Hisoblash](#sla-ish-vaqti-hisoblash)
   - [Xodimlar KPI Samaradorlik Formulasi](#xodimlar-kpi-samaradorlik-formulasi)
   - [Elektron Navbat Qabul Slotlari Generatori](#elektron-navbat-qabul-slotlari-generatori)
6. [O'rnatish, Ishga Tushirish va Konfiguratsiya](#6-ornatish-ishga-tushirish-va-konfiguratsiya)
   - [Lokal Ishga Tushirish](#lokal-ishga-tushirish)
   - [Docker va Docker Compose](#docker-va-docker-compose)
   - [Ishlab Chiqarish Muhitiga Deploy Qilish (Production)](#ishlab-chiqarish-muhitiga-deploy-qilish-production)
7. [API Endpointlar Xaritasi](#7-api-endpointlar-xaritasi)
8. [Avtomatlashtirilgan Testlar va Sifat Nazorati](#8-avtomatlashtirilgan-testlar-va-sifat-nazorati)
9. [Loyiha Tuzilishi (Kataloglar Daraxti)](#9-loyiha-tuzilishi-kataloglar-daraxti)
10. [Kelajakdagi Rivojlanish Rejalari](#10-kelajakdagi-rivojlanish-rejalari)

---

## 1. Loyiha Haqida

Registrator ofisi axborot tizimi universitetda ta'lim sifatini oshirish, talabalarga davlat xizmatlari va ma'lumotnomalar berish jarayonini to'liq raqamlashtirish, inson omilini kamaytirish hamda korrupsiyaviy xatarlarning oldini olishga qaratilgan.

### Asosiy Tamoyillar:
- **Shaffoflik:** Har bir ariza va qabul navbati aniq xronologiya (Audit Trail) va unikal identifikator bilan kuzatib boriladi.
- **Ijro Intizomi (SLA):** Belgilangan muddatdan o'tgan yoki kechikayotgan har qanday ariza bo'yicha rahbariyatga avtomatik signal beriladi.
- **Ob'ektiv KPI:** Xodim faoliyatiga sub'ektiv baho emas, balki bajarilgan xizmatlar murakkabligi, muddati va talabaning to'g'ridan-to'g'ri reytingi ta'sir qiladi.
- **Maxfiylik (Privacy-First):** Talabaning pasport ma'lumotlari yoki PINFL bazada saqlanmaydi (PII himoyasi).

---

## 2. Texnologik Stek

| Qatlam | Texnologiya | Izoh |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.12+ / FastAPI 0.115+ | Yuqori tezlikdagi to'liq asinxron RESTful API |
| **ORM & Ma'lumotlar Bazasi** | SQLAlchemy 2.0 (AsyncIO), PostgreSQL / SQLite | Relyatsion me'morchilik, migratsiya va tranzaksiyalar xavfsizligi |
| **Ma'lumotlar Validatsiyasi** | Pydantic v2 & Pydantic-Settings | Sxemalar, xatolar tahlili va muhit o'zgaruvchilari |
| **Xavfsizlik & Autentifikatsiya** | JWT (PyJWT), PBKDF2-HMAC-SHA256 | Xavfsiz tuzlangan parollar va rolli sessiyalar (RBAC) |
| **Integratsiya** | HTTPX (Asinxron) | JBNUU HEMIS API (`https://student.jbnuu.uz/rest/v1`) integratsiyasi |
| **Bildirishnomalar & Bot** | Telegram Bot API & Aiogram / Asinxron Webhook | Avtomatik xabarnomalar va 30-minutlik eslatmalar |
| **Frontend** | Vanilla HTML5, Tailwind CSS, Vanilla JS, Chart.js | Fremvorksiz, tezkor, engil va responsiv interfeyslar |
| **Konteynerlashtirish** | Docker, Docker Compose | Ishlab chiqarish serverida izolyatsiyalangan micro-servislar |
| **Avtomatlashtirilgan Testlar** | Pytest, Pytest-AsyncIO, HTTPX AsyncClient | 53 ta keng qamrovli integratsion va regressiya testlari |

---

## 3. Tizim Arxitekturasi va Rollar (RBAC)

Namunaviy Nizom talablariga muvofiq Registrator ofisida foydalanuvchi rollari va ularning vakolatlari qat'iy chegaralangan:

```
                                 ┌─────────────────────────────────────────┐
                                 │   O'quv ishlari bo'yicha Prorektor      │
                                 │    (Oliy nazorat, 3-bosqich qarori)     │
                                 └────────────────────┬────────────────────┘
                                                      │
                                 ┌────────────────────▼────────────────────┐
                                 │       Registrator ofisi Boshlig'i       │
                                 │   (Umumiy boshqaruv, SLA, 2-bosqich)    │
                                 └───────────┬─────────────────┬───────────┘
                                             │                 │
                   ┌─────────────────────────▼────┐        ┌───▼──────────────────────────┐
                   │    FRONT OFFICE (104-xona)   │        │         BACK OFFICE          │
                   │    Bevosita darchalar qabuli │        │   Ma'lumotlar bazasi/tahlil  │
                   └─────────────┬────────────────┘        └──────────────┬───────────────┘
                                 │                                        │
          ┌──────────────────────┼──────────────────────┐                 ├─ 1. Statistik tahlil sektori
          │                      │                      │                 ├─ 2. O'quv jarayonini muvofiqlashtirish
    ┌─────▼────────┐       ┌─────▼────────┐       ┌─────▼────────┐        └─ 3. Hujjatlar va arxiv sektori
    │  1-Darcha    │       │  2-Darcha    │       │  3-Darcha    │
    │  Ma'lumot-   │       │  Moliya va   │       │  Ilmiy va    │
    │  nomalar     │       │  shartnoma   │       │  xalqaro     │
    └──────────────┘       └──────────────┘       └──────────────┘
```

### Rollar bo'yicha imkoniyatlar matritsasi:

| Rol kodi | Nomi | Vakolatlari |
| :--- | :--- | :--- |
| `student` | Talaba | HEMIS orqali kirish, onlayn ariza yuborish, elektron navbat taloni olish, natijani baholash (1–5⭐), e'tiroz bildirish (`dispute`). |
| `front_staff` | Front-ofis xodimi | 104-xona darchalarida (1, 2, 3-darchalar) bevosita qabul o'tkazish, navbat chaqirish, arizalarga rasmiy QR fayllar yuklash. |
| `back_staff` | Back-ofis xodimi | Statistik tahlil, o'quv jarayonini muvofiqlashtirish, arxiv va buyruqlar bilan ishlash, murakkab arizalarni ijro etish. |
| `office_head` | Ofis boshlig'i | Arizalarni xodimlarga taqsimlash, ping-pong qayta yo'naltirishning oldini olish, SLA intizomi, 2-bosqich nizolarini ko'rib chiqish, KPI nazorati. |
| `vice_rector` | O'quv ishlari bo'yicha Prorektor | 3-bosqichga eskalatsiya qilingan eng bahsli arizalar bo'yicha yakuniy majburiy qaror chiqarish, tahliliy dashboard va infografika. |
| `admin` | Tizim administratori | Yangi xodimlar yaratish, rollar va darchalarni biriktirish, ta'lim shakli siyosatini sozlash, kalendar yuritish, to'liq audit jurnalini nazorat qilish. |

---

## 4. Asosiy Modullar va Imkoniyatlar

### 4.1. Talabalar Portali (`portal.html`)
- **HEMIS Yagona Kirish:** Talaba o'zining HEMIS talaba ID va paroli orqali kiradi. 48 soatlik xavfsiz JWT sessiya yaratiladi.
- **Onlayn Arizalar:** Sirtqi va masofaviy ta'lim shakli talabalari xizmat turi bo'yicha fayl ilova qilgan holda 24/7 rejimida murojaat yo'llaydi.
- **Elektron Navbat Olish:** 09:00 dan 17:00 gacha 15 daqiqalik qabul oraliqlarida talon band qilish.
- **Bosmaga Chiqariladigan QR Talon Modali (`print-ticket-modal`):**
  - Talabaning ismi, fakulteti, xizmat turi, darcha raqami, unikal talon kodi (`TALON-MMDD-XXXX`), QR-kod va qabul vaqti ko'rsatilgan chiroyli chek modali.
  - Bir bosishda printerga yoki PDF ga chiqarish imkoniyati (`window.print()`).
- **Natijani 5 Yulduzli Baholash Modali (`rating-modal`):**
  - Ijro yakunlangach, talaba xizmat sifatini 1 dan 5 yulduzgacha baholaydi va izoh qoldiradi. Ushbu baho ijrochining oylik KPI reytingiga bevosita ko'paytiruvchi koeffitsiyent sifatida ta'sir qiladi.
- **72 Soatlik Asoslantirilgan E'tiroz Modali (`dispute-modal`):**
  - Agar talaba ijro natijasidan norozi bo'lsa, 72 soat ichida ariza bo'yicha asoslantirilgan vajlarini kiritib, e'tiroz bildiradi.
- **Rasmiy Javob Fayllari:** Xodim tomonidan biriktirilgan tasdiqlangan hujjatlarni bevosita yuklab olish.

### 4.2. Xodimlar va Rahbariyat Ish Stoli (`staff.html`)
- **Rolga Qarab Moslashuvchi Interfeys:** Foydalanuvchi tizimga kirishi bilan uning roliga qarab navigatsiya menyulari avtomatik filtrlanadi.
- **Murojaatlar Monitoringi:** Statuslar (Yangi, Jarayonda, Bajarilgan, Rad etilgan, Nizoli, Eskalatsiya qilingan) va SLA taymerlari (Yashil, Sariq, Qizil svetofor).
- **Darcha Qabuli (Navbat Boshqaruvi):**
  - Bugungi kunga olingan navbatlar ro'yxati;
  - "Chaqirish" tugmasi bosilganda televizor tablosida ovozli e'lon yangraydi va talabaning Telegramiga darhol xabar boradi;
  - "Qabulni yakunlash" orqali qabul muvaffaqiyatli yopiladi.
- **Xodimlar KPI Reytingi:** Real vaqt rejimida barcha xodimlarning bajarilgan ballari, jarimalari va reyting foizi.
- **Ta'lim Shakli Cheklovlari (Policy):** Qaysi ta'lim shakli (Kunduzgi, Sirtqi, Masofaviy) qaysi xizmatlarga onlayn ariza yuborishi mumkinligini boshqarish.
- **Bayramlar Taqvimi:** Dam olish va rasmiy bayram kunlarini kiritish (ushbu kunlarda SLA taymerlari avtomatik muzlatiladi).

### 4.3. Jonli Navbat Tablosi (`board.html` / `display.html`)
- **104-Xona Televizor Monitori:** Katta ekranlar uchun mo'ljallangan zamonaviy to'q mavzudagi interfeys.
- **3 ta Darcha Holati:** Har bir darchada (1-darcha, 2-darcha, 3-darcha) ayni paytda qaysi talon chaqirilgani, xizmat nomi va talabaning ismi yonib turadi.
- **Audio Ovozli E'lon:** Yangi talon chaqirilganda brauzerning Web Speech API orqali avtomatik o'zbek tilida ovoz yangraydi:
  > *"Diqqat! TALON-0919-4821 raqamli talaba, 1-darchaga marhamat!"*
- **Kutish Zali Ro'yxati:** Keyingi navbat kutayotgan talabalar ro'yxati va ularning taxminiy qabul vaqti.
- **Fullscreen Rejimi:** Klaviaturadagi `F11` yoki "To'liq ekran" tugmasi orqali brauzer panellarisiz ko'rsatish.
- **Avtomatik Sinxronizatsiya:** Har 5 soniyada server bilan fonda xavfsiz yangilanadi.

### 4.4. Rahbariyat Infografik Tahliliy Dashboardi
- **Davr Bo'yicha Filtrlash:** Barcha davr, Joriy oy, Oxirgi 30 kun, Joriy yil.
- **4 ta Strategik Ko'rsatkich:**
  1. Jami murojaatlar soni va bajarilish foizi;
  2. SLA ijro intizomi (o'z vaqtida yopilgan arizalar ulushi %);
  3. O'rtacha ijro tezligi (ariza tushganidan to ijrogacha bo'lgan vaqt soatlarda);
  4. Talabalar mamnuniyat reytingi (o'rtacha yulduzcha 5.0 shkalasida).
- **4 ta Interaktiv Chart.js Diagrammasi:**
  - *Fakultetlar kesimida murojaatlar:* Qaysi fakultet talabalari eng ko'p murojaat qilayotgani bo'yicha qiyosiy ustunli diagramma;
  - *Top-5 eng talabgir xizmatlar:* Eng ko'p so'ralayotgan xizmatlar reytingi;
  - *Holatlar taqsimoti (Doughnut):* Bajarilgan, ko'rib chiqilayotgan, nizoli va rad etilgan arizalar proporsiyasi;
  - *14 kunlik dinamika trendi (Line):* Murojaatlar kelib tushishi va yakunlanishi sur'ati.
- **Batafsil Fakultetlar Tahliliy Jadvali:** Har bir fakultet bo'yicha jami arizalar, yakunlanganlar, nizolar soni va qoniqish reytingi.
- **Excel (CSV) Eksport:** Barcha hisobotlarni bir zumda rasmiy Excel formatida yuklab olish.

### 4.5. Real-Vaqt Audio va Jonli Indikatorlar (Live Badges)
- **Web Audio API Orqali Ogohlantirish:** Xodim ish stolida yangi murojaat kelib tushganda brauzerda 2-ohangli chiroyli qo'ng'iroq chalinadi (880Hz -> 1320Hz).
- **Ovoz Boshqaruvi:** Headerdagi tugma orqali ovozli ogohlantirishlarni yoqish yoki o'chirish mumkin (sozlama `localStorage` da saqlanadi).
- **Jonli Nishonlar (Live Badges):** Har 15 soniyada yangilanuvchi ko'rsatkichlar:
  - Yangi kelib tushgan va ko'rilmagan arizalar soni (Qizil pulsatsiyali nishon);
  - Darcha qabulida navbat kutayotgan talabalar soni (Moviy nishon).

### 4.6. Telegram Bot va Foniy Eslatmalar Tizimi
- **Murojaatlar Holati Xabarlari:**
  - Ariza ijrochiga biriktirilganda: *"Sizning murojaatingiz ijrochiga yo'naltirildi"*;
  - Ijro yakunlanganda: *"Murojaatingiz ko'rib chiqildi, rasmiy javob yuklandi. Iltimos portalda baholang"*;
  - Prorektor qaror chiqarganda: *"Prorektor yakuniy qarori qabul qilindi"*.
- **Elektron Navbat Xabarlari:**
  - Talon olinganda: *"Siz 104-xonaga qabulga yozildingiz. Talon raqamingiz: TALON-..."*;
  - Xodim chaqirganda: *"Sizning navbatingiz keldi! 1-darchaga marhamat qiling"*.
- **30 Daqiqa Oldin Avtomatik Eslatma (Fon Vazifasi):**
  - `sla_reminder.py` foniy vazifasi har daqiqada qabul jadvallarini tekshiradi.
  - Qabul vaqtiga 30 daqiqa qolganda talabaning Telegramiga eslatma jo'natiladi:
    > *"⏰ Eslatma: Sizning Registrator ofisidagi qabulingizga 30 daqiqa qoldi. Iltimos, 104-xonaga o'z vaqtida kelishingizni so'raymiz."*

### 4.7. Nizolarni 3 Bosqichli Eskalatsiya Qilish va Prorektor Qarori
1. **1-bosqich (Ijrochi xodim):** Xodim ma'lumotnomani tayyorlaydi va tizimga yuklaydi.
2. **2-bosqich (Ofis boshlig'i):** Talaba norozi bo'lib e'tiroz bildirsa (`dispute`), masala xodimga emas, to'g'ridan-to'g'ri Boshliqqa o'tadi. Boshliq nizoni xolis ko'rib chiqadi.
3. **3-bosqich (O'quv ishlari bo'yicha Prorektor):** Agar nizo filial darajasidagi vakolatni talab qilsa, Boshliq uni Prorektorga eskalatsiya qiladi.
   - Prorektor ish stolida binafsharang **"Prorektor qarorini chiqarish"** modali ochiladi.
   - Unda talaba e'tirozi, dastlabki xulosa va boshliq bildirgisini o'rganib, Prorektor o'zining yakuniy qat'iy va majburiy xulosasini kiritadi.
   - Qaror tasdiqlanishi bilan nizo qat'iy yopiladi, barcha tomonlarga Telegram xabari boradi.
- **Murojaat Xronologiyasi va Audit Trail Modali (`appeal-audit-modal`):**
  - Har bir arizaning butun hayot sikli (Kelib tushishi, Biriktirilishi, Xodim javobi, Talaba e'tirozi, Eskalatsiya va Yakuniy qaror) aniq vaqt belgilari va rangli kartochkalar ko'rinishida ko'rsatiladi.

### 4.8. Tizim Xavfsizligi va Markaziy Audit Jurnali
- **AuditLog Modeli:** Har qanday muhim tizim amali `audit_logs` jadvalida xavfsiz qayd etiladi.
- **Qamrab Olingan Operatsiyalar:**
  - Tizimga kirish amallari (`auth:login`);
  - Yangi xodim yaratish (`user:create_staff`);
  - Xodim rolini o'zgartirish (`user:update_role`);
  - Parol va hisob ma'lumotlarini yangilash (`user:update_credentials`);
  - Navbat chaqirish (`appointment:call`) va yakunlash (`appointment:complete`);
  - Murojaatlar bo'yicha barcha o'zgarishlar va qarorlar.
- **RBAC Himoyalangan API:** `GET /api/v1/audit-logs` endpointiga faqat Administrator, Boshliq va Prorektor ruxsatga ega. Talabalar va oddiy xodimlar uchun `403 Forbidden`.
- **Interaktiv Audit Jurnali Paneli (`staff.html` da):**
  - Obyektlar (`auth`, `appeal`, `appointment`, `user`, `role`, `service`, `department`) bo'yicha filtr;
  - Amallar (`login`, `create`, `update`, `call`, `complete`, `dispute`) bo'yicha filtr;
  - Matnli qidiruv (foydalanuvchi, IP, amal yoki o'zgarishlar tafsiloti);
  - 4 ta real-vaqt statistika ko'rsatkichi;
  - To'liq jurnallarni Excel (CSV) formatida eksport qilish.

---

## 5. Biznes Mantiq, Formula va Algoritmlar

### SLA Ish Vaqti Hisoblash

Murojaatlarning ijro muddati sun'iy kechikishlarga yo'l qo'ymaslik uchun faqat rasmiy ish vaqtida hisoblanadi:
- **Ish kunlari:** Dushanba – Shanba (09:00 dan 17:00 gacha);
- **Tushlik tanaffusi:** 13:00 dan 14:00 gacha (ijro taymeridan chegirib tashlanadi);
- **Dam olish kunlari:** Yakshanba hamda rasmiy davlat bayramlari;
- Agar murojaat ish vaqtidan tashqari yoki dam olish kuni kelsa, hisoblash keyingi ish kuni soat 09:00 dan boshlanadi.

```python
# Algoritm mantiqi (app/services/sla_calculator.py)
# Dushanba-Shanba 09:00-13:00 va 14:00-17:00 (kuniga 7 soat sof ish vaqti)
# Yakshanba va 'holidays' jadvalida kiritilgan sanalar butunlay aylanib o'tiladi.
```

### Xodimlar KPI Samaradorlik Formulasi

Xodimning oylik reytingi va samaradorlik ko'rsatkichi quyidagi shaffof algoritm orqali hisoblanadi:

$$\text{Sof Ball} = \max(0, \text{Bajarilgan Ball} - \text{Jarima Ballari})$$

$$\text{Baho Koeffitsiyenti} = \frac{\text{Talabalar Bergan O'rtacha Reyting (1.0 - 5.0)}}{5.0}$$

$$\text{KPI Foizi} = \left( \frac{\text{Sof Ball}}{\text{Oylik Reja (150 ball)}} \right) \times \text{Baho Koeffitsiyenti} \times 100$$

- *SLA buzilishi uchun jarima:* Har bir muddati o'tgan ariza uchun **-5 ball**;
- *Talaba bahosi ko'paytiruvchisi:* Agar xodim arizalarni tez yopsa-yu, lekin sifatsiz xizmat ko'rsatib 1-2 yulduz olsa, uning umumiy KPI ko'rsatkichi avtomatik pasayadi.

### Elektron Navbat Qabul Slotlari Generatori

- Ish vaqti (09:00–17:00) 15 daqiqalik intervallarga bo'linadi (jami 28 ta slot);
- Tushlik vaqti (13:00–14:00) avtomatik chiqarib tashlanadi;
- O'tib ketgan soatlar, band qilingan vaqtlar va yakshanba kunlari dinamik filtrlanadi;
- Soat 17:00 dan oshganda tizim avtomatik ravishda keyingi ish kunining ertalabki qabuliga yo'naltiradi.

---

## 6. O'rnatish, Ishga Tushirish va Konfiguratsiya

### Lokal Ishga Tushirish

1. **Repozitoriyani yuklab olish:**
   ```bash
   git clone https://github.com/shohabbosdev/Roffice_Appeal.git
   cd Roffice_Appeal
   ```

2. **Python virtual muhitini faollashtirish:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   # .venv\Scripts\activate   # Windows
   ```

3. **Kutubxonalarni o'rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Muhit sozlamalari (`.env`):**
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./data/roffice.db
   SECRET_KEY=super_secret_production_key_change_in_env
   HEMIS_API_URL=https://student.jbnuu.uz/rest/v1
   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   TELEGRAM_BOT_USERNAME=your_bot_username
   CORS_ORIGINS=["*"]
   ```

5. **Dastlabki ma'lumotlarni bazaga yuklash (Seed data):**
   ```bash
   python seed_data.py
   ```

6. **Serverni ishga tushirish:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

### Docker va Docker Compose

Ishlab chiqarish yoki sinov muhitida to'liq xizmatlarni (FastAPI + SQLite/Postgres) bir buyruq bilan ko'tarish:

```bash
docker compose up -d --build
```

Konteynerlar holatini tekshirish:
```bash
docker compose ps
docker compose logs -f backend
```

---

### Ishlab Chiqarish Muhitiga Deploy Qilish (Production)

Loyiha O'zMU Jizzax filiali rasmiy ishlab chiqarish serverida muvaffaqiyatli faoliyat yuritmoqda:
- **Server:** `jbnuu.uz` (Ubuntu Server, Nginx Reverse Proxy, Docker Engine)
- **Katalog:** `/var/www/Roffice_Appeal`
- **Jonli URL:** `https://jbnuu.uz/roffice-appeal/`

Deploy qilish qadamlari:
```bash
ssh jbnuu
cd /var/www/Roffice_Appeal
git pull origin main
docker compose up -d --build backend
```

Salomatlik holatini tekshirish:
```bash
curl -s https://jbnuu.uz/roffice-appeal/health
# Javob: {"status":"healthy"}
```

---

## 7. API Endpointlar Xaritasi

Swagger interaktiv hujjatlari: `http://localhost:8000/docs` yoki `https://jbnuu.uz/roffice-appeal/docs`

```
Autentifikatsiya va Foydalanuvchilar:
  POST   /api/v1/auth/login                         - Talaba va xodimlar yagona kirish darchasi
  POST   /api/v1/auth/hemis/login                   - HEMIS talabalar kirishi
  GET    /api/v1/auth/me                            - Joriy foydalanuvchi profili
  GET    /api/v1/users/staff                        - Barcha xodimlar ro'yxati (Boshliq/Admin)
  POST   /api/v1/users/staff                        - Yangi xodim qo'shish (Admin)
  PATCH  /api/v1/users/{user_id}/role               - Xodim rolini o'zgartirish (Admin)
  POST   /api/v1/users/me/credentials               - Login/parolni yangilash

Murojaatlar (Appeals):
  GET    /api/v1/appeals                            - Murojaatlar ro'yxati (filtrlar, sahifalash)
  POST   /api/v1/appeals                            - Yangi onlayn ariza yuborish (Talaba)
  GET    /api/v1/appeals/{id}                       - Ariza tafsiloti va xronologiyasi
  PATCH  /api/v1/appeals/{id}/assign                - Ijrochiga biriktirish (Boshliq)
  PATCH  /api/v1/appeals/{id}/resolve               - Ijro javobini yuklash va yopish (Xodim)
  POST   /api/v1/appeals/{id}/confirm               - Natijani tasdiqlash va baholash (Talaba)
  POST   /api/v1/appeals/{id}/dispute               - Natijaga e'tiroz bildirish (Talaba)
  POST   /api/v1/appeals/{id}/prorektor-decision    - Yakuniy majburiy qaror (Prorektor)
  GET    /api/v1/appeals/analytics/executive        - Rahbariyat tahliliy infografikasi

Elektron Navbat (Appointments):
  GET    /api/v1/appointments/available-slots       - Bo'sh qabul vaqtlari (detailed=true)
  POST   /api/v1/appointments/book                  - Talon band qilish (Talaba)
  GET    /api/v1/appointments/my                    - Talabaning barcha talonlari
  GET    /api/v1/appointments/today                 - Bugungi navbatlar (Xodim ish stoli)
  GET    /api/v1/appointments/queue-board           - Jonli televizor tablosi ma'lumotlari
  PATCH  /api/v1/appointments/{id}/call             - Navbatni chaqirish (Audio e'lon)
  PATCH  /api/v1/appointments/{id}/complete         - Qabulni yakunlash
  DELETE /api/v1/appointments/{id}                  - Navbatni bekor qilish

Audit va Tizim Loglari:
  GET    /api/v1/audit-logs                         - Markaziy audit jurnali (Admin/Boshliq/Prorektor)

Xizmatlar va Bo'limlar:
  GET    /api/v1/services                           - Xizmatlar katalogi
  POST   /api/v1/services                           - Yangi xizmat qo'shish
  GET    /api/v1/departments                        - Darchalar va bo'limlar ro'yxati

Fayllar va Hujjatlar:
  POST   /api/v1/uploads                            - Fayl yuklash (MIME va Magic Bytes tekshiruvli)
  GET    /uploads/{filename}                        - Faylni xavfsiz yuklab olish

Telegram Integratsiyasi:
  GET    /api/v1/telegram/info                      - Bot havolasi va QR kod
  POST   /api/v1/telegram/webhook                   - Telegram Webhook yangilanishlari
```

---

## 8. Avtomatlashtirilgan Testlar va Sifat Nazorati

Loyihada **test-driven reliability** tamoyili joriy etilgan. Barcha biznes mantiq, avtorizatsiya qoidalari, SLA formulalari va xavfsizlik cheklovlari avtomatik testlar bilan qoplangan.

### Testlarni ishga tushirish:
```bash
.venv/bin/pytest tests/ -v
```

### Test natijalari:
```
tests/test_appeals_flow.py ......................... [  5%]
tests/test_appointments.py ......................... [  7%]
tests/test_audit_trail_system.py ................... [ 13%]
tests/test_calendar_api.py ......................... [ 15%]
tests/test_detailed_slots.py ....................... [ 18%]
tests/test_dispute_escalation.py ................... [ 22%]
tests/test_education_form_policy.py ................ [ 24%]
tests/test_executive_analytics.py .................. [ 26%]
tests/test_hemis_auth.py ........................... [ 30%]
tests/test_kpi_system.py ........................... [ 37%]
tests/test_live_badges.py .......................... [ 39%]
tests/test_live_queue_board.py ..................... [ 41%]
tests/test_prorektor_decision_desk.py .............. [ 47%]
tests/test_services_crud.py ........................ [ 50%]
tests/test_sla_calculator.py ....................... [ 64%]
tests/test_staff_crud_and_credentials.py ........... [ 69%]
tests/test_staff_services_assignment.py ............ [ 71%]
tests/test_student_portal_actions.py ............... [ 77%]
tests/test_telegram_automated_notifications.py ..... [ 83%]
tests/test_telegram_integration.py ................. [ 92%]
tests/test_uploads.py .............................. [ 94%]
tests/test_users_and_unified_login.py .............. [100%]

============================== 53 passed in 8.47s ==============================
```

---

## 9. Loyiha Tuzilishi (Kataloglar Daraxti)

```
Roffice_Appeal/
├── app/
│   ├── api/
│   │   ├── deps.py                    # JWT va RBAC rolli bog'lanishlar (get_current_user)
│   │   └── v1/
│   │       ├── router.py              # API v1 markaziy marshrutizatori
│   │       ├── auth.py                # Kirish, HEMIS SSO, xodim va talaba tokenlari
│   │       ├── users.py               # Xodimlarni boshqarish, rollar, parollarni o'zgartirish
│   │       ├── appeals.py             # Murojaatlar, biriktirish, xulosa, tahliliy API
│   │       ├── appointments.py        # Elektron navbat, talonlar, live-board, slotlar
│   │       ├── audit.py               # Markaziy audit loglari API endpointi
│   │       ├── services.py            # Xizmatlar va darchalar CRUD boshqaruvi
│   │       ├── calendar.py            # Bayramlar va dam olish kunlari kalendari
│   │       ├── kpi.py                 # Xodimlar KPI reytingi va jarimalar
│   │       ├── telegram.py            # Telegram bot webhook va bog'lanish
│   │       └── uploads.py             # Fayllarni xavfsiz qabul qilish (Magic Bytes)
│   ├── core/
│   │   ├── config.py                  # Pydantic muhit konfiguratsiyalari
│   │   ├── database.py                # Asinxron SQLAlchemy sessiyasi
│   │   └── security.py                # Parollarni xeshlash va JWT generatsiyasi
│   ├── models/
│   │   └── __init__.py                # Barcha relyatsion modellar (User, Appeal, Appointment...)
│   ├── schemas/
│   │   └── __init__.py                # Pydantic v2 validatsiya va javob sxemalari
│   ├── services/
│   │   ├── appeal_service.py          # Murojaatlar hayot sikli biznes mantiqi
│   │   ├── queue_service.py           # Elektron navbat va slotlar mantiqi
│   │   ├── audit_service.py           # Markazlashgan xavfsizlik va harakatlar auditi
│   │   ├── hemis_client.py            # O'zMU Jizzax filiali HEMIS REST API mijozi
│   │   ├── telegram_service.py        # Telegram bildirishnomalari va bot funksiyalari
│   │   ├── sla_calculator.py          # Ish vaqti va muddatlarni hisoblash algoritmi
│   │   └── sla_reminder.py            # Orqa fondagi davriy eslatmalar (30-minutlik eslatma)
│   ├── static/
│   │   ├── portal.html                # Talabalar asosiy portali (Arizalar, Navbat, Baholash)
│   │   ├── staff.html                 # Xodimlar, Boshliq, Prorektor va Admin ish stoli
│   │   ├── login.html                 # Yagona xavfsiz avtorizatsiya darchasi
│   │   ├── board.html                 # Katta televizorlar uchun jonli navbat tablosi
│   │   └── display.html               # Navbat tablosi muqobil yo'nalishi
│   └── main.py                        # FastAPI asosiy ilovasi, fon vazifalari va CORS
├── tests/                             # 53 ta avtomatlashtirilgan Pytest testlari
├── uploads/                           # Yuklangan tasdiqlovchi rasmiy hujjatlar
├── docker-compose.yml                 # Docker Compose konfiguratsiyasi
├── Dockerfile                         # Python 3.12 Backend konteyner ta'rifi
├── requirements.txt                   # Kerakli Python kutubxonalari
├── seed_data.py                       # Dastlabki namunaviy ma'lumotlar generatori
└── README.md                          # Loyihaning to'liq texnik qo'llanmasi
```

---

## 10. Kelajakdagi Rivojlanish Rejalari

Loyihani yanada takomillashtirish va kengaytirish uchun quyidagi yo'nalishlar rejalashtirilgan:
1. **Avtomatik Zaxira Nusxalash (Automated Backup):** Ma'lumotlar bazasini har kecha shifrlangan holda S3 yoki masofaviy xavfsiz serverga zaxiralash.
2. **HEMIS Real-Vaqt Webhook:** Talaba o'qish holati (kursdan qolish, akademik ta'til) o'zgarganda tizimda profilni zudlik bilan yangilash.
3. **SMS Xabarnomalar:** Telegram botga ulanmagan talabalar uchun qabul navbati to'g'risida to'g'ridan-to'g'ri SMS ogohlantirish (Eskiz.uz shlyuzi orqali).
4. **Talabalar Fikr-Mulohaza AI Tahlili:** Talabalarning baholash va e'tiroz matnlarini tabiiy tilni qayta ishlash (NLP) orqali tahlil qilib, eng ko'p shikoyat qilinayotgan sohalarni avtomatik aniqlash.

---

**Muallif va Ishlab chiquvchi:** Registrator ofisi raqamlashtirish jamoasi • O'zbekiston Milliy universiteti Jizzax filiali  
**Litsenziya:** O'zMU Jizzax filiali ichki foydalanish huquqi asosida himoyalangan.
