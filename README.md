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

## Tizim Rollari va Funksional Vazifalar Xaritasi (RBAC & Nizom Muvofiqligi)

O'zbekiston Respublikasi Oliy ta'lim, fan va innovatsiyalar vazirligining 2025-yil 24-fevraldagi 73-sonli buyrug'i (Namunaviy Nizom) talablariga binoan Registrator ofisida har bir rol va sektorning vazifalari hamda javobgarlik chegarasi quyidagicha qat'iy belgilangan:

```
                                 ┌─────────────────────────────────────────┐
                                 │   O'quv ishlari bo'yicha Prorektor      │
                                 │     (Oliy nazorat, 3-bosqich qarori)    │
                                 └────────────────────┬────────────────────┘
                                                      │
                                 ┌────────────────────▼────────────────────┐
                                 │       Registrator ofisi Boshlig'i       │
                                 │   (Umumiy boshqaruv, SLA, 2-bosqich)    │
                                 └───────────┬─────────────────┬───────────┘
                                             │                 │
                  ┌──────────────────────────▼───┐         ┌───▼──────────────────────────┐
                  │   FRONT OFFICE (104-xona)    │         │         BACK OFFICE          │
                  │   Bevosita darchalar qabuli  │         │   Ma'lumotlar bazasi/tahlil  │
                  └──────────────┬───────────────┘         └──────────────┬───────────────┘
                                 │                                        │
         ┌───────────────────────┼───────────────────────┐                ├─ 1. Statistik tahlil sektori
         │                       │                       │                ├─ 2. O'quv jarayonini muvofiqlashtirish
   ┌─────▼────────┐        ┌─────▼────────┐        ┌─────▼────────┐       └─ 3. Hujjatlar va arxiv sektori
   │  1-Darcha    │        │  2-Darcha    │        │  3-Darcha    │
   │  Ma'lumot-   │        │  Moliya va   │        │  Ilmiy va    │
   │  nomalar     │        │  shartnoma   │        │  xalqaro     │
   └──────────────┘        └──────────────┘        └──────────────┘
```

---

### 1. Talaba (`student`)
- **Vazifasi:** Tizimning asosiy iste'molchisi (mijoz).
- **Asosiy amallari:**
  - HEMIS yagona talaba akkaunti (`student.jbnuu.uz`) orqali kirish (2 kunlik xavfsiz sessiya).
  - Sirtqi va masofaviy ta'lim shakllari: portal orqali 24/7 rejimida onlayn murojaat yo'llash.
  - Kunduzgi ta'lim shakli: 104-xonaga "Kelib hal etish" bo'yicha 15 daqiqalik elektron navbat taloni (`TALON-MMDD-XXXX`) olish.
  - Murojaat ijro etilgach, tayyor QR-kodli rasmiy faylni yuklab olish.
  - Natijani 1 dan 5 yulduzgacha baholash (baho xodimning KPI ko'rsatkichiga to'g'ridan-to'g'ri ta'sir qiladi).
  - Natijadan norozi bo'lsa, 72 soat ichida asoslantirilgan e'tiroz (`dispute`) bildirish.
- **Cheklovlari:** Boshqa talabalarning murojaatlari yoki talonlarini ko'ra olmaydi; kunduzgi ta'lim talabasi ruxsat berilmagan xizmatlarga onlayn ariza yubora olmaydi (faqat navbat oladi).

---

### 2. Front-ofis xodimi (`front_staff` — 104-xona darchalari)
- **1-Darcha: Talabalarga xizmat ko'rsatish va ma'lumotnomalar sektori:**
  - O'qish joyidan QR-kodli elektron ma'lumotnoma berish (SLA: 2 soat).
  - Rasmiy transkript va baholar ko'chirmasini taqdim etish (SLA: 24 soat).
  - Sirtqi/masofaviy talabalarga imtihon sessiyasi chaqiruv qog'ozini shakllantirish.
  - Talabaning shaxsiy GPA ko'rsatkichi ma'lumotnomasini chiqarish.
  - HEMIS tizimi login va parolini tiklab berish.
  - Darcha qabulida 15 daqiqalik elektron navbat taloni bo'yicha qabul qilish va yakunlash.
- **2-Darcha: Buxgalteriya, to'lovlar va stipendiya sektori:**
  - To'lov-kontrakt shartnoma summasini hisoblash, rasmiylashtirish va qaydnoma yuritish.
  - Qayta o'qish (kreditlarni qayta topshirish) uchun to'lov miqdorini aniqlash va shartnoma berish.
  - Talabalar stipendiyasi va moddiy yordam arizalarini birlamchi qabul qilish.
  - Ijara to'lovi subsidiyasi va talabalar turar joyiga joylashish arizalarini ro'yxatga olish.
  - Bitiruvchilarni ishga taqsimlash yo'llanmalari va qaydnomalarini rasmiylashtirish.
- **3-Darcha: Ilmiy-innovatsion faoliyat va xalqaro aloqalar sektori:**
  - O'qish joyidan ingliz tilida rasmiy ma'lumotnomalar tayyorlash.
  - Xalqaro grantlar, akademik mobillik dasturlari va "El-yurt umidi" tanlovlari bo'yicha maslahat berish.
  - Xorijlik talabalarni tizimda ro'yxatga olish, viza va vaqtinchalik ro'yxatdan o'tkazish xizmatlari.
  - Nomdor davlat stipendiyalari, ilmiy konferensiyalar va startap tanlovlari arizalarini qabul qilish.
- **Front-ofis KPI mezonlari:** Har bir yakunlangan darcha qabuli va xizmat uchun 2 dan 10 ballgacha; talabalarning bergan o'rtacha bahosi koeffitsiyenti; SLA buzilishi uchun har bir kechikishga -5 jarima bali.

---

### 3. Back-ofis mutaxassisi (`back_staff` — Tahlil va arxiv)
- **1-Sektor: Statistik ma'lumotlarni yuritish va tahlil sektori:**
  - Talabalar kontingenti, resurslar, shartnoma to'lovlari va o'zlashtirish tahliliy hisobotlarini yuritish.
  - Talabalar safidan chetlashtirilgan, kursda qoldirilgan va akademik ta'tildagilar statistikasini tuzish.
  - Statistika agentligi va vazirlikka yuboriladigan shakllarni shakllantirish.
  - HEMIS ga kiritilayotgan statistik ma'lumotlar to'g'riligini doimiy audit qilish.
- **2-Sektor: O'quv jarayonini muvofiqlashtirish sektori:**
  - Akademik guruhlarni shakllantirish, talabalarni tanlov fanlariga va tyutorlarga biriktirish.
  - Qayta o'qish fan guruhlari, dars jadvallari va oraliq/yakuniy nazoratlar grafiklarini tizimga kiritish.
  - Talabalar harakati buyruqlari loyihalarini ishlab chiqish (o'qishni ko'chirish, tiklash, chetlashtirish, kursdan kursga o'tkazish).
  - HEMIS orqali kunlik davomat monitoringini yuritish.
- **3-Sektor: Talabalar hujjatlarini yuritish va arxiv sektori:**
  - Bitiruvchilarning shaxsiy yig'majildlarini to'plash, tikish va arxivga topshirish.
  - Qat'iy hisobdagi blankalar (diplom, diplom ilovasi, sertifikatlar) hisobi va berilishini yuritish.
  - Diplomlarning haqiqiyligini tekshirish (`d-arxiv.edu.uz`, `mehnat.uz`) va tashkilotlar so'rovlariga rasmiy javob berish.
  - Yo'qotilgan diplom va ilovalar o'rniga dublikat berish arizalarini ekspertiza qilish.
- **Back-ofis KPI mezonlari:** Nizomiy xizmat vazifalari ijrosi (Boshliq tomonidan tasdiqlangan bildirgi asosida), murakkab arizalarni o'z vaqtida hal etish ko'rsatkichi (oylik 150 ballik reja).

---

### 4. Registrator ofisi boshlig'i (`office_head`)
- **Vazifasi:** Ofis faoliyatini umumiy boshqarish, tezkor ijro intizomi va xizmat sifatini ta'minlash.
- **Asosiy amallari:**
  - Barcha Front va Back xodimlarga kelib tushgan murojaatlarni taqsimlash va yo'naltirish.
  - Ijrochilar o'rtasida "ping-pong"ning oldini olish: qayta yo'naltirish 1 martadan oshganda avtomatik o'ziga qulflanadi.
  - SLA ijro muddatlarini real vaqt rejimida kuzatish (Qizil, Sariq, Yashil svetofor monitoringi).
  - **2-bosqich ichki nizo:** Talaba ijro natijasiga e'tiroz bildirsa (`dispute`), ariza ijrochiga qaytmaydi, to'g'ridan-to'g'ri boshliq tomonidan ko'rib chiqiladi.
  - Hal etilmagan murakkab nizolarni O'quv ishlari bo'yicha prorektorga (3-bosqich) eskalatsiya qilish.
  - Xodimlarning oylik KPI hisobotini ko'rib chiqish, jarima (-5 ball) yoki qo'shimcha rag'bat ballarini berish.

---

### 5. O'quv ishlari bo'yicha prorektor (`vice_rector`)
- **Vazifasi:** Ofis ustidan oliy nazorat va yakuniy qaror qabul qiluvchi instansiya.
- **Asosiy amallari:**
  - Boshliq tomonidan 3-bosqichga eskalatsiya qilingan eng murakkab yoki bahsli arizalar bo'yicha yakuniy majburiy qaror chiqarish.
  - Prorektorning qarori kiritilishi bilan nizo qat'iy yopiladi va talabaga rasmiy yakuniy xat jo'natiladi.
  - Talabalar apellyatsiya komissiyasi faoliyatiga rahbarlik qilish.
  - Tizimdagi umumiy oylik KPI va tahliliy ko'rsatkichlarni monitoring qilish.

---

### 6. Administrator (`admin`)
- **Vazifasi:** Axborot tizimining texnik va ma'muriy barqarorligini ta'minlash.
- **Asosiy amallari:**
  - Yangi xodimlarni yaratish, ularga rollar va xizmat vazifalarini biriktirish, vaqtinchalik parollarni boshqarish.
  - Registrator ofisi sohalari/sektorlari va darcha raqamlarini yaratish va tahrirlash.
  - Xizmatlar katalogini yuritish (nomi, tavsifi, tegishli darcha, KPI bali, SLA soati).
  - Ta'lim shakllari bo'yicha onlayn murojaat cheklov siyosatini boshqarish (`/appeals/policy/education-forms`).
  - Bayram va dam olish kunlari kalendarini yuritish (ushbu kunlarda taymerlar muzlaydi va navbat berilmaydi).
  - Tizim xavfsizligi, API integratsiyalari va ma'lumotlar bazasi butunligini nazorat qilish.

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
8. **Elektron Navbatda O'tgan Vaqtlarni Bloklash Mexanizmi:**
   - "Kelib hal etish" bo'limida o'tmishdagi sanalarga talon olish butunlay cheklandi. Bugungi kun tanlanganida esa faqat joriy daqiqadan keyingi bo'sh qabul vaqtlari ko'rsatiladigan va o'tib ketgan slotlarga ariza topshirish bloklanadigan qilindi.

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
