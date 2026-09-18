import os
from PIL import Image, ImageDraw, ImageFont

# Set up canvas dimensions (A4 portrait: 1600 x 2262 pixels)
W, H = 1600, 2262
img = Image.new("RGB", (W, H), "#FFFFFF")
draw = ImageDraw.Draw(img)

# Fonts setup
FONT_PATH = "C:\\Windows\\Fonts\\segoeui.ttf"
FONT_BOLD_PATH = "C:\\Windows\\Fonts\\segoeuib.ttf"
FONT_MONO_PATH = "C:\\Windows\\Fonts\\arial.ttf"

def get_font(bold=False, size=20):
    p = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.truetype("arial.ttf", size)

# Color Palette (Official Corporate / Architectural)
C_NAVY_DARK = "#0F172A"
C_NAVY = "#1E293B"
C_PRIMARY = "#0284C7"
C_PRIMARY_DARK = "#0369A1"
C_BG_CARD = "#F8FAFC"
C_BORDER = "#CBD5E1"
C_TEXT_DARK = "#0F172A"
C_TEXT_MUTED = "#475569"
C_TEXT_LIGHT = "#64748B"

# Accent colors (Subtle, non-sticker, purely informational)
C_GREEN = "#15803D"
C_GREEN_BG = "#DCFCE7"
C_AMBER = "#B45309"
C_AMBER_BG = "#FEF3C7"
C_RED = "#B91C1C"
C_RED_BG = "#FEE2E2"
C_PURPLE = "#6B21A8"
C_PURPLE_BG = "#F3E8FF"
C_BLUE = "#0369A1"
C_BLUE_BG = "#E0F2FE"

# Margins
PAD_X = 70
CUR_Y = 50

# --- HEADER ---
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 115], fill="#0F172A", outline="#0284C7", width=2)

draw.text((PAD_X + 30, CUR_Y + 18), "OLIY TA'LIM MUASSASASI REGISTRATOR OFISI", fill="#38BDF8", font=get_font(True, 15))
draw.text((PAD_X + 30, CUR_Y + 42), "TALABALARNING ELEKTRON MUROJAATLARI BILAN ISHLASH TIZIMI JARAYONLAR XARITASI", fill="#FFFFFF", font=get_font(True, 23))
draw.text((PAD_X + 30, CUR_Y + 78), "Standartlar: ITIL 4, AACRAO, ISO 9001  |  Arxitektura: FastAPI, PostgreSQL, Redis, Telegram Bot", fill="#94A3B8", font=get_font(False, 14))

CUR_Y += 135

def draw_stage_header(number, title, subtitle, color):
    global CUR_Y
    # Top bar
    draw.rectangle([PAD_X, CUR_Y, PAD_X + 110, CUR_Y + 28], fill=color)
    draw.text((PAD_X + 10, CUR_Y + 4), f"{number}-BOSQICH", fill="#FFFFFF", font=get_font(True, 13))
    
    draw.text((PAD_X + 125, CUR_Y + 4), title, fill=C_NAVY_DARK, font=get_font(True, 16))
    if subtitle:
        w_t = draw.textlength(title, font=get_font(True, 16))
        draw.text((PAD_X + 135 + int(w_t), CUR_Y + 6), f"({subtitle})", fill=C_TEXT_LIGHT, font=get_font(False, 13))
    
    CUR_Y += 36

def draw_box(x, y, w, h, title, desc, tag_text=None, tag_bg="#E2E8F0", tag_fg="#1E293B", border_left_color=None):
    # Background
    draw.rectangle([x, y, x + w, y + h], fill="#FFFFFF", outline=C_BORDER, width=1)
    if border_left_color:
        draw.rectangle([x, y, x + 5, y + h], fill=border_left_color)
    
    # Title
    t_x = x + 14
    draw.text((t_x, y + 10), title, fill=C_NAVY_DARK, font=get_font(True, 14))
    
    # Desc (multiline)
    d_y = y + 34
    lines = desc.split("\n")
    for line in lines:
        draw.text((t_x, d_y), line, fill=C_TEXT_MUTED, font=get_font(False, 12))
        d_y += 18
    
    # Tag
    if tag_text:
        tag_font = get_font(True, 10)
        t_w = int(draw.textlength(tag_text, font=tag_font)) + 12
        t_h = 20
        tag_y = y + h - 28
        draw.rectangle([t_x, tag_y, t_x + t_w, tag_y + t_h], fill=tag_bg)
        draw.text((t_x + 6, tag_y + 3), tag_text, fill=tag_fg, font=tag_font)

def draw_arrow_down(y_from, y_to, x=W//2):
    draw.line([(x, y_from), (x, y_to)], fill="#94A3B8", width=2)
    draw.polygon([(x - 5, y_to - 6), (x + 5, y_to - 6), (x, y_to)], fill="#94A3B8")

# ==========================================
# 1-BOSQICH: AUTENTIFIKATSIYA VA FILTRLAR
# ==========================================
draw_stage_header("1", "TALABA KIRISHI, HEMIS INTEGRATSIYASI VA XAVFSIZLIK FILTRLARI", "Veb-portal va Telegram Bot", C_PRIMARY)

box_w = (W - PAD_X * 2 - 30) // 4
h1 = 150
y1 = CUR_Y

draw_box(PAD_X + 0 * (box_w + 10), y1, box_w, h1, 
         "1.1. HEMIS OAuth 2.0", 
         "Talaba shaxsiy login-paroli\nbilan kiradi. Tizimda 2 kunlik\nxavfsiz JWT-seans yaratiladi.\nTalaba anketasi avtomat olinadi.",
         "Xatolik: 0%", C_BLUE_BG, C_BLUE, C_PRIMARY)

draw_box(PAD_X + 1 * (box_w + 10), y1, box_w, h1, 
         "1.2. Da'vo Muddati Filtri", 
         "Statute of Limitations:\nEski semestr yoki o'tgan\ndavrdagi arizalar rad etiladi.\n(Bahoga e'tiroz: 5 ish kuni).",
         "Me'yoriy muddat", C_AMBER_BG, C_AMBER, C_AMBER)

draw_box(PAD_X + 2 * (box_w + 10), y1, box_w, h1, 
         "1.3. Anti-Spam / Anti-Flood", 
         "Bir xil mavzuda ko'rib\nchiqilayotgan faol arizasi\nbo'lgan talabaga yangi takroriy\nmurojaat ochish bloklanadi.",
         "Tirbandlik to'sig'i", C_RED_BG, C_RED, C_RED)

draw_box(PAD_X + 3 * (box_w + 10), y1, box_w, h1, 
         "1.4. Arizani Bekor Qilish", 
         "Self-Service Withdrawal:\nXodim ishga olgunga qadar\ntalaba o'z xatosini tushunsa,\narizani bekor qila oladi.",
         "Vaqtni tejash", C_GREEN_BG, C_GREEN, C_GREEN)

CUR_Y += h1 + 10
draw_arrow_down(CUR_Y - 5, CUR_Y + 12)
CUR_Y += 18

# ==========================================
# 2-BOSQICH: TOIFALAR VA ISH VAQTI (SLA)
# ==========================================
draw_stage_header("2", "MUROJAAT TOIFALARI VA ISH VAQTI (SLA) REGLAMENTI", "24/7 qabul, ish vaqtida ijro", C_PURPLE)

box_w3 = (W - PAD_X * 2 - 20) // 3
h2 = 135
y2 = CUR_Y

draw_box(PAD_X + 0 * (box_w3 + 10), y2, box_w3, h2,
         "2.1. 1-Toifa: Tezkor Murojaatlar",
         "O'qish joyidan ma'lumotnoma (spravka),\nHEMIS parolini tiklash, standart arizalar.\nMas'ul bo'linma: Front bo'limi.",
         "IJRO: 1 ISH KUNI (24h)", C_GREEN_BG, C_GREEN, C_GREEN)

draw_box(PAD_X + 1 * (box_w3 + 10), y2, box_w3, h2,
         "2.2. 2-Toifa: O'rta Murakkablikdagi",
         "To'lov-shartnoma, kredit ma'lumotlari,\ndars jadvalida nomuvofiqlik, transkript.\nMas'ul bo'linma: Front / Backend.",
         "IJRO: 3 ISH KUNI (72h)", C_BLUE_BG, C_BLUE, C_BLUE)

draw_box(PAD_X + 2 * (box_w3 + 10), y2, box_w3, h2,
         "2.3. 3-Toifa: Murakkab / Kollegial",
         "Akademik ta'til, ko'chirish/tiklash,\nfan farqlari, komissiya apellyatsiyasi.\nMas'ul: Backend va Fakultet komissiyasi.",
         "IJRO: 5-7 ISH KUNI", C_PURPLE_BG, C_PURPLE, C_PURPLE)

CUR_Y += h2 + 8

# Business Hours Info Bar
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 36], fill="#F1F5F9", outline="#CBD5E1")
draw.text((PAD_X + 14, CUR_Y + 9), "AQLLI ISH SOATLARI (Business Hours SLA):", fill=C_NAVY_DARK, font=get_font(True, 12))
draw.text((PAD_X + 320, CUR_Y + 9), "Taymer faqat Dushanba-Juma 09:00-18:00 oralig'ida hisoblanadi. Dam olish va bayramlarda muzlaydi.", fill=C_TEXT_MUTED, font=get_font(False, 12))
draw.text((W - PAD_X - 350, CUR_Y + 9), "Avto-xabar: dam olish kuni talabaga boradi", fill=C_PRIMARY_DARK, font=get_font(True, 11))

CUR_Y += 46
draw_arrow_down(CUR_Y - 5, CUR_Y + 12)
CUR_Y += 18

# ==========================================
# 3-BOSQICH: BOSHLIQ TAQSIMOTI VA ICHKI VAZIFALAR
# ==========================================
draw_stage_header("3", "OFIS BOSHLIG'I TAQSIMOTI VA ICHKI BO'LIMLAR", "Front va Backend o'rtasida shaffoflik", C_PRIMARY)

box_w = (W - PAD_X * 2 - 30) // 4
h3 = 145
y3 = CUR_Y

draw_box(PAD_X + 0 * (box_w + 10), y3, box_w, h3,
         "3.1. Boshliq Taqsimoti",
         "Arizalarni o'rganadi va tegishli\nxodimlarga yo'naltiradi.\n12 soatda botga eslatma.\n24 soatda avto-taqsimot (Fail-Safe).",
         "Taqsimlash SLA: 24h", C_AMBER_BG, C_AMBER, C_AMBER)

draw_box(PAD_X + 1 * (box_w + 10), y3, box_w, h3,
         "3.2. Front Bo'limi",
         "Mijozlar bilan bevosita darcha:\nTezkor ma'lumotnomalar berish,\nariza blankalarini qabul qilish,\nkonsultatsiya va tushuntirish.",
         "Operativ darcha", C_BLUE_BG, C_BLUE, C_BLUE)

draw_box(PAD_X + 2 * (box_w + 10), y3, box_w, h3,
         "3.3. Backend Bo'limi",
         "Ichki akademik mutaxassislar:\nHEMIS akademik baholarini tuzatish,\nbuyruqlar, rasmiy transkriptlar,\nfan farqlari va qarzdorliklar.",
         "Baza va Buyruqlar", C_PURPLE_BG, C_PURPLE, C_PURPLE)

draw_box(PAD_X + 3 * (box_w + 10), y3, box_w, h3,
         "3.4. Ping-Pong Cheklovi",
         "Xodim arizani boshqasiga faqat\n1 marta qaytara oladi. Agar yana\nrad etilsa, Boshliq stoliga 'Ichki\nnizo' maqomi bilan qulflanadi.",
         "Futbol qilishga to'siq", C_RED_BG, C_RED, C_RED)

CUR_Y += h3 + 10
draw_arrow_down(CUR_Y - 5, CUR_Y + 12)
CUR_Y += 18

# ==========================================
# 4-BOSQICH: SVETOFOR NAZORATI VA TAYMER PAUZALARI
# ==========================================
draw_stage_header("4", "SVETOFOR INTIZOM NAZORATI VA TAYMERNI TO'XTATISH QOIDALARI", "Xodimni asossiz jarimadan himoya", C_AMBER)

box_w = (W - PAD_X * 2 - 30) // 4
h4 = 135
y4 = CUR_Y

draw_box(PAD_X + 0 * (box_w + 10), y4, box_w, h4,
         "4.1. Yashil Zona (0-50%)",
         "Me'yordagi ijro holati.\nXodim arizani qabul qilgan\nva tegishli tartibda ko'rib\nchiqishni amalga oshirmoqda.",
         "Holat: Normal", C_GREEN_BG, C_GREEN, C_GREEN)

draw_box(PAD_X + 1 * (box_w + 10), y4, box_w, h4,
         "4.2. Sariq Zona (50-80%)",
         "Ogohlantirish zonasi.\nMuddatning 80% o'tganda\nxodimning Telegram botiga\nshoshiltiruvchi signal boradi.",
         "Holat: Ogohlantirish", C_AMBER_BG, C_AMBER, C_AMBER)

draw_box(PAD_X + 2 * (box_w + 10), y4, box_w, h4,
         "4.3. Qizil Zona (OVERDUE)",
         "Muddati o'tdi (100%+).\nXodimning KPI reytingidan jarima\nchegiriladi, Boshliqqa favqulodda\nxabar va qayta taqsimlash imkoni.",
         "Holat: Jarima (KPI)", C_RED_BG, C_RED, C_RED)

draw_box(PAD_X + 3 * (box_w + 10), y4, box_w, h4,
         "4.4. Taymer Pauzalari",
         "A) Chala ariza (Request Clarify):\nTaymer to'xtaydi (talaba kutilyapti).\nB) Tashqi xulosa (Pending External):\nDekanat xulosasi davrida muzlaydi.",
         "Xodim himoyasi", C_BLUE_BG, C_BLUE, C_BLUE)

CUR_Y += h4 + 10
draw_arrow_down(CUR_Y - 5, CUR_Y + 12)
CUR_Y += 18

# ==========================================
# 5-BOSQICH: 72 SOATLIK TASDIQLASH VA NATIJA
# ==========================================
draw_stage_header("5", "72 SOATLIK TASDIQLASH SEANSI, NATIJA VA KORRUPSIYAGA QARSHI TIZIM", "QR-kodli PDF va 3 ta yakuniy yo'l", C_GREEN)

# Status bar
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 32], fill="#F8FAFC", outline="#CBD5E1")
draw.text((PAD_X + 14, CUR_Y + 7), "NATIJA TAYYOR BO'LGANDA:", fill=C_NAVY_DARK, font=get_font(True, 12))
draw.text((PAD_X + 220, CUR_Y + 7), "Xodim QR-kod va Hash bilan himoyalangan rasmiy PDF biriktiradi -> 72 soatlik tasdiqlash boshlanadi (24h va 48h da bot eslatma beradi).", fill=C_TEXT_MUTED, font=get_font(False, 12))

CUR_Y += 40

box_w3 = (W - PAD_X * 2 - 20) // 3
h5 = 165
y5 = CUR_Y

draw_box(PAD_X + 0 * (box_w3 + 10), y5, box_w3, h5,
         "5.1. [TASDIQLANDI] - HAL BO'LDI",
         "Talaba bot orqali tasdiqlaydi va 1-5 baho beradi.\nKorrupsiyaga qarshi: Xodim qaysi talaba qanday\nbaho qo'yganini ko'ra olmaydi (bosim yo'q).\n1 va 2 bahoga majburiy sabab yoziladi.\nMurojaat to'liq 'RESOLVED' deb yopiladi.",
         "STATUS: RESOLVED (Yopildi)", C_GREEN_BG, C_GREEN, C_GREEN)

draw_box(PAD_X + 1 * (box_w3 + 10), y5, box_w3, h5,
         "5.2. [AVTOMATIK YOPILISH]",
         "Talaba 72 soat davomida (2 ta eslatmaga qaramay)\nhech qanday javob bermasa, tizim arizani avtomat\n'Tizim tomonidan qabul qilindi' deb yopadi.\nXodim hisobotiga sun'iy to'siq bo'lib qolmaydi.\nStatistika va KPI saqlanadi.",
         "STATUS: AUTO_CLOSED", C_BLUE_BG, C_BLUE, C_BLUE)

draw_box(PAD_X + 2 * (box_w3 + 10), y5, box_w3, h5,
         "5.3. [E'TIROZ] - ESKALATSIYA",
         "Talaba 'Hal bo'lmadi' desa, XODIMGA QAYTMAYDI!\nTo'g'ridan-to'g'ri Ofis Boshlig'iga (Tier-2) boradi.\nBoshliq xodimni jazolaydi yoki asosli javob beradi.\nAgar kelishuv bo'lmasa, O'quv Prorektoriga (Tier-3)\nyakuniy va qat'iy qaror uchun yuboriladi.",
         "STATUS: DISPUTE_ESCALATED", C_RED_BG, C_RED, C_RED)

CUR_Y += h5 + 20

# ==========================================
# FOOTER / QO'SHIMCHA MEZONLAR
# ==========================================
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 70], fill="#0F172A", outline="#1E293B")

f_col_w = (W - PAD_X * 2) // 3
draw.text((PAD_X + 20, CUR_Y + 14), "OMMAVIY ARIZALAR (MASTER TICKET)", fill="#38BDF8", font=get_font(True, 12))
draw.text((PAD_X + 20, CUR_Y + 36), "30+ talabaning bir xil arizasi 1 ta\nasosiy ariza orqali bir zumda yopiladi.", fill="#CBD5E1", font=get_font(False, 11))

draw.text((PAD_X + f_col_w + 20, CUR_Y + 14), "100% AUDIT TRAIL VA LOGLAR", fill="#38BDF8", font=get_font(True, 12))
draw.text((PAD_X + f_col_w + 20, CUR_Y + 36), "Har bir soniya, harakat, fayl va izoh\nbazada abadiy qonuniy dalil bo'lib saqlanadi.", fill="#CBD5E1", font=get_font(False, 11))

draw.text((PAD_X + f_col_w * 2 + 20, CUR_Y + 14), "YURIDIK KUCH VA VERIFIKATSIYA", fill="#38BDF8", font=get_font(True, 12))
draw.text((PAD_X + f_col_w * 2 + 20, CUR_Y + 36), "QR-kod orqali istalgan tashkilot hujjat\naslini serverdan onlayn tekshira oladi.", fill="#CBD5E1", font=get_font(False, 11))

# Output path
out_path = "c:\\Users\\Veon Admin\\Downloads\\Roffice_Appeal\\Registrator_Ofisi_Jarayonlar_Xaritasi_A4.png"
img.save(out_path, "PNG", quality=95)
print(f"Blueprint successfully created at: {out_path}")
