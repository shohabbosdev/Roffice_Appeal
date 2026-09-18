# Registrator Ofisi — Murojaatlar, Elektron Navbat va KPI Axborot Tizimi

Mirzo Ulug'bek nomidagi O'zbekiston Milliy universiteti Jizzax filialining Registrator ofisi talabalar murojaatlari, "Kelib hal etish" elektron navbat tizimi va xodimlar KPI samaradorligini avtomatlashtirilgan baholash platformasi.

---

## Mundarija
- [Loyiha Haqida](#loyiha-haqida)
- [Asosiy Imkoniyatlar](#asosiy-imkoniyatlar)
- [Texnologik Stek](#texnologik-stek)
- [Tizim Rollari va Vakolatlari (RBAC)](#tizim-rollari-va-vakolatlari-rbac)
- [Biznes Mantiq va Reglament](#biznes-mantiq-va-reglament)
  - [SLA Ish Vaqti Hisoblash](#sla-ish-vaqti-hisoblash)
  - [Xodimlar KPI Samaradorlik Formulasi](#xodimlar-kpi-samaradorlik-formulasi)
  - [Nizolarni 3 Bosqichli Eskalatsiya Qilish](#nizolarni-3-bosqichli-eskalatsiya-qilish)
- [Audit va Amalga Oshirilgan Tuzatishlar](#audit-va-amalga-oshirilgan-tuzatishlar)
- [O'rnatish va Ishga Tushirish](#ornatish-va-ishga-tushirish)
  - [Lokal Muhitda](#lokal-muhitda)
  - [Docker Yordamida](#docker-yordamida)
- [API Hujjatlari](#api-hujjatlari)
- [GitHub Repozitoriyasi Bilan Integratsiya](#github-repozitoriyasi-bilan-integratsiya)

---

## Loyiha Haqida

Registrator ofisi axborot tizimi O'zbekiston Respublikasi Oliy ta'lim, fan va innovatsiyalar vazirligining me'yoriy hujjatlari hamda filial nizomiga asosan ishlab chiqilgan. Tizim talabalar va universitet ma'muriyati o'rtasidagi munosabatlarni shaffoflashtirish, inson omilini kamaytirish, korrupsiyaviy xavflarni bartaraf etish hamda ijro intizomini real vaqt rejimida nazorat qilishga xizmat qiladi.

---

## Asosiy Imkoniyatlar

1. **Yagona Autentifikatsiya (SSO / HEMIS):**
   - Talabalar uchun O'zMU Jizzax filiali HEMIS axborot tizimi (`https://student.jbnuu.uz/rest/v1`) orqali 2 kunlik (48 soat) xavfsiz sessiya.
   - Registrator ofisi xodimlari va rahbariyat uchun rolli mahalliy tizimga kirish.
2. **Shaxsga Doir Ma'lumotlar Maxfiyligi (PII Himoyasi):**
   - Talabalarning pasport seriyasi, PINFL va yashash manzillari bazada saqlanmaydi, faqat akademik ma'lumotlar (fakultet, yo'nalish, kurs, guruh) olinadi.
3. **Rolga Asoslangan Onlayn Murojaatlar:**
   - Ta'lim shakllari (kunduzgi, sirtqi, masofaviy) bo'yicha dinamik ruxsat siyosati.
   - Murojaatni ijrochiga biriktirish, tushuntirish so'rash (taymerni muzlatish) va rasmiy javob yuklash.
4. **"Kelib Hal Etish" — Darcha Qabuli va Elektron Navbat:**
   - 09:00 dan 17:00 gacha 15 daqiqalik qabul oraliqlari (tushlik 13:00–14:00 inobatga olingan).
   - Unikal elektron navbat talonlari (`TALON-MMDD-XXXX`).
   - Terminal orqali shaxsiy Check-in tasdiqlash.
5. **Avtomatlashtirilgan KPI Baholash:**
   - Oylik standart 150 ballik reja.
   - Talaba tomonidan berilgan baholar (1–5 yulduzcha) va bajarilgan xizmatlar murakkabligiga qarab shaffof reyting.
6. **Telegram Bot Integratsiyasi:**
   - Har bir arizaning holati, ijro javobi va elektron navbat talonlari to'g'ridan-to'g'ri Telegram bot orqali yetkaziladi.
   - Universitet xodimlari va talabalarini HEMIS telefon raqami orqali avtomatik bog'lash.

---

## Texnologik Stek

- **Backend:** Python 3.12+, FastAPI 0.115+
- **Asinxron ORM:** SQLAlchemy 2.0 (AsyncIO), aiosqlite / asyncpg
- **Ma'lumotlar Validatsiyasi:** Pydantic v2, Pydantic-Settings
- **Xavfsizlik:** JWT (PyJWT), PBKDF2-HMAC-SHA256 (tuzlangan xesh)
- **HTTP Mijoz:** HTTPX (Asinxron HEMIS API mijoz)
- **Konteynerlashtirish:** Docker, Docker Compose
- **Testlash:** Pytest, Pytest-AsyncIO

---

## Tizim Rollari va Vakolatlari (RBAC)

| Rol | Kodi | Asosiy Vakolatlari |
| :--- | :--- | :--- |
| **Talaba** | `student` | Onlayn murojaat yo'llash, navbat taloni olish, natijani tasdiqlash va baholash, e'tiroz bildirish. |
| **Front-ofis xodimi** | `front_staff` | Darcha qabuli (1, 2, 3-darchalar), ma'lumotnoma va transkript berish, shartnoma arizalarini ko'rib chiqish. |
| **Back-ofis mutaxassisi** | `back_staff` | Arxiv ma'lumotnomalari, GPA tahlili, o'qishni tiklash va akademik tahlil bo'yicha ijro. |
| **Registrator ofisi boshlig'i** | `office_head` | Ijro intizomi nazorati, arizalarni qayta yo'naltirish, ichki nizolarni hal qilish, xodimlar KPI ballarini audit qilish. |
| **O'quv ishlari bo'yicha prorektor** | `vice_rector` | Eskalatsiya qilingan murakkab nizoli masalalar bo'yicha yakuniy majburiy qaror qabul qilish. |
| **Administrator** | `admin` | Tizim konfiguratsiyasi, sohalar/darchalar katalogi, bayramlar taqvimi va xodimlarni boshqarish. |

---

## Biznes Mantiq va Reglament

### SLA Ish Vaqti Hisoblash
Murojaatlarning ijro muddati faqat rasmiy ish vaqtida hisoblanadi:
- **Ish kunlari:** Dushanba – Shanba (09:00 dan 17:00 gacha).
- **Dam olish kunlari:** Yakshanba hamda rasmiy davlat bayramlari.
- **Tushlik tanaffusi:** 13:00 dan 14:00 gacha (ijro taymeridan chegirib tashlanadi).
- Agar murojaat ish vaqtidan tashqari yoki dam olish kuni yuborilsa, hisoblash keyingi ish kuni soat 09:00 dan boshlanadi.

### Xodimlar KPI Samaradorlik Formulasi
Har bir xodimning oylik ko'rsatkichi quyidagi algoritm asosida shakllanadi:
$$\text{Sof Ball} = \max(0, \text{Bajarilgan Ball} - \text{Jarima Ballari})$$
$$\text{Baho Koeffitsiyenti} = \frac{\text{O'rtacha Reyting}}{5.0}$$
$$\text{KPI Foizi} = \left( \frac{\text{Sof Ball}}{\text{Oylik Reja (150)}} \right) \times \text{Baho Koeffitsiyenti} \times 100$$

### Nizolarni 3 Bosqichli Eskalatsiya Qilish
1. **1-bosqich (Ijrochi):** Front/Back mutaxassis murojaatni ko'rib chiqadi va rasmiy javob beradi.
2. **2-bosqich (Boshliq):** Agar talaba 72 soat ichida "Hal bo'lmadi" deb e'tiroz bildirsa, ariza xodimga qaytarilmasdan to'g'ridan-to'g'ri Registrator ofisi boshlig'iga o'tadi.
3. **3-bosqich (Prorektor):** Boshliq tomonidan yechilmagan nizolar O'quv ishlari bo'yicha prorektorga yo'naltiriladi va prorektorning qarori bilan qat'iy yakunlanadi.

---

## Audit va Amalga Oshirilgan Tuzatishlar

Loyiha ustida olib borilgan chuqur texnik audit natijasida quyidagi kamchiliklar bartaraf etildi:

1. **KPI Ballari Dublikatlanishi Tuzatildi:**
   - Ilgari xodim javob berganda (`resolve`) hamda talaba tasdiqlaganda (`confirm`) KPI ballari takroran qo'shilar edi. Endi ball faqat talaba tasdiqlaganda yoki 72 soat o'tib avtomatik yopilganda bir marta yoziladi.
2. **72 Soatlik Avto-Yopilish Fonga Ulandi:**
   - `AppealService.auto_close_expired` funksiyasi `sla_reminder.py` dagi davriy 15 daqiqalik fon jarayoniga biriktirildi.
3. **Talon Kodlari To'qnashuvi Bartaraf Etildi:**
   - Elektron navbat talonlari formati unikal sana va xesh bilan kengaytirildi (`TALON-MMDD-XXXX`), bu takrorlanish xavfini yo'qotdi.
4. **IDOR Zaifligi Yopildi:**
   - Navbatni Check-in qilish endpointida faqat talon egasi bo'lgan talaba yoki vakolatli xodim tasdiqlashi mumkin bo'lgan ruxsat tekshiruvi joriy etildi.
5. **SLA Algoritmiga Tushlik Tanaffusi Kiritildi:**
   - 13:00–14:00 tushlik oralig'i murojaat ijro muddatini hisoblashdan avtomatik chegiriladigan bo'ldi.
6. **Xotira Xavfsizligi Ta'minlandi:**
   - SLA eslatmalari to'plami (`_reminded_set`) doimiy ravishda faol arizalar bilan sinxronlanib, xotira tozalab boriladi.
7. **CORS Siyosati Xavfsizlashtirildi:**
   - Wildcard origin o'rniga aniq ishonchli domenlar belgilandi.

---

## O'rnatish va Ishga Tushirish

### Lokal Muhitda

1. **Repozitoriyani klonlash:**
   ```bash
   git clone https://github.com/shohabbosdev/Roffice_Appeal.git
   cd Roffice_Appeal
   ```

2. **Virtual muhitni yaratish va faollashtirish:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   ```

3. **Kutubxonalarni o'rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfiguratsiya faylini tayyorlash:**
   ```bash
   cp .env.example .env
   # .env faylini o'z sozlamalaringiz bilan tahrirlang
   ```

5. **Dastlabki ma'lumotlarni bazaga yuklash:**
   ```bash
   python seed_data.py
   ```

6. **Serverni ishga tushirish:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Yordamida

Docker va Docker Compose yordamida tizimni bitta buyruq orqali ishga tushirish mumkin:

```bash
docker-compose up -d --build
```
Tizim holatini tekshirish:
```bash
curl http://localhost:8000/health
```

---

## API Hujjatlari

Server ishga tushgach, interaktiv Swagger va ReDoc hujjatlaridan foydalanish mumkin:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc UI:** `http://localhost:8000/redoc`
- **Tizim portali:** `http://localhost:8000/portal`
- **Talaba kabineti:** `http://localhost:8000/student`
- **Xodim ish stoli:** `http://localhost:8000/staff`

---

## GitHub Repozitoriyasi Bilan Integratsiya

Loyiha rasmiy GitHub omboriga ulangan:
- **Repozitoriya:** [https://github.com/shohabbosdev/Roffice_Appeal.git](https://github.com/shohabbosdev/Roffice_Appeal.git)
- **Asosiy tarmoq:** `main`

### O'zgarishlarni yuborish:
```bash
git add .
git commit -m "feat: audit kamchiliklari bartaraf etildi va arxitektura mustahkamlandi"
git branch -M main
git remote add origin https://github.com/shohabbosdev/Roffice_Appeal.git
git push -u origin main
```
