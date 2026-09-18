import os
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions: 1600 x 2262 (A4 ratio)
W, H = 1600, 2262
img = Image.new("RGB", (W, H), "#0B132B") # Deep executive navy background
draw = ImageDraw.Draw(img)

FONT_PATH = "C:\\Windows\\Fonts\\segoeui.ttf"
FONT_BOLD_PATH = "C:\\Windows\\Fonts\\segoeuib.ttf"

def get_font(bold=False, size=20):
    p = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.truetype("arial.ttf", size)

PAD_X = 75
CUR_Y = 60

# --- 1. HEADER SECTION ---
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 120], fill="#1C2541", outline="#3A506B", width=2)
draw.text((PAD_X + 30, CUR_Y + 20), "UNIVERSITET REGISTRATOR OFISI | REAL HAYOTIY KEYS", fill="#48CAE4", font=get_font(True, 16))
draw.text((PAD_X + 30, CUR_Y + 48), "Masofaviy talabaning murojaati qanday hal etiladi?", fill="#FFFFFF", font=get_font(True, 28))
draw.text((PAD_X + 30, CUR_Y + 86), "3-kurs masofaviy ta'lim talabasi Sardor Aliyev misolida to'liq raqamli zanjir", fill="#94D2BD", font=get_font(False, 16))

CUR_Y += 140

# --- 2. ISHTIROKCHILAR (PERSONAJLAR PANELI) ---
draw.text((PAD_X, CUR_Y), "JARAYON QATNASHCHILARI (ROLLAR)", fill="#E2E8F0", font=get_font(True, 18))
CUR_Y += 30

char_w = (W - PAD_X * 2 - 30) // 4
h_char = 95
chars = [
    ("TALABA", "Sardor Aliyev", "Masofaviy ta'lim, 3-kurs\n(Viloyatdan turib yozadi)", "#0284C7"),
    ("OFIS BOSHLIG'I", "Akrom Vohidov", "Arizani ko'rib yo'naltiradi\n(Nazoratchi va Hakam)", "#4F46E5"),
    ("FRONT XODIMI", "Malika Karimova", "Tezkor ma'lumotnoma beradi\n(1 ish kuni - 24h ijrochi)", "#059669"),
    ("PROREKTOR", "O'quv ishlari bo'yicha", "Nizoli holatlarda qat'iy\nyakuniy qaror chiqaruvchi", "#DC2626")
]

for i, (role, name, desc, color) in enumerate(chars):
    x = PAD_X + i * (char_w + 10)
    draw.rectangle([x, CUR_Y, x + char_w, CUR_Y + h_char], fill="#1C2541", outline=color, width=2)
    draw.rectangle([x, CUR_Y, x + char_w, CUR_Y + 26], fill=color)
    draw.text((x + 10, CUR_Y + 5), role, fill="#FFFFFF", font=get_font(True, 12))
    draw.text((x + 10, CUR_Y + 33), name, fill="#FFFFFF", font=get_font(True, 14))
    
    lines = desc.split("\n")
    for j, l in enumerate(lines):
        draw.text((x + 10, CUR_Y + 54 + j * 16), l, fill="#94A3B8", font=get_font(False, 11))

CUR_Y += h_char + 35

# --- 3. TIMELINE STEPS ---
draw.text((PAD_X, CUR_Y), "BOSQICHMA-BOSQICH IJRO XRONOLOGIYASI", fill="#E2E8F0", font=get_font(True, 18))
CUR_Y += 30

TIMELINE_X = PAD_X + 65
CARD_X = PAD_X + 155
CARD_W = W - PAD_X - CARD_X

def draw_step(time_str, step_num, title, action_title, details, result_badge, border_color):
    global CUR_Y
    card_h = 190
    
    # Timeline badge
    draw.rectangle([TIMELINE_X - 55, CUR_Y + 10, TIMELINE_X + 55, CUR_Y + 62], fill="#1C2541", outline=border_color, width=2)
    draw.text((TIMELINE_X - 35, CUR_Y + 16), "Soat", fill="#94A3B8", font=get_font(False, 12))
    draw.text((TIMELINE_X - 35, CUR_Y + 34), time_str, fill="#FFFFFF", font=get_font(True, 20))
    
    # Connecting line
    draw.line([(TIMELINE_X, CUR_Y + 62), (TIMELINE_X, CUR_Y + card_h + 20)], fill="#3A506B", width=3)
    
    # Card
    draw.rectangle([CARD_X, CUR_Y, CARD_X + CARD_W, CUR_Y + card_h], fill="#1C2541", outline="#334155", width=1)
    draw.rectangle([CARD_X, CUR_Y, CARD_X + 6, CUR_Y + card_h], fill=border_color)
    
    # Title
    draw.text((CARD_X + 24, CUR_Y + 14), f"{step_num}. {title}", fill="#FFFFFF", font=get_font(True, 18))
    draw.text((CARD_X + 24, CUR_Y + 42), action_title, fill=border_color, font=get_font(True, 13))
    
    # Details
    d_y = CUR_Y + 70
    for d in details:
        draw.text((CARD_X + 24, d_y), d, fill="#CBD5E1", font=get_font(False, 13))
        d_y += 24
        
    # Result badge
    if result_badge:
        bw = int(draw.textlength(result_badge, font=get_font(True, 12))) + 20
        draw.rectangle([CARD_X + CARD_W - bw - 20, CUR_Y + 14, CARD_X + CARD_W - 20, CUR_Y + 44], fill="#0B132B", outline=border_color, width=1)
        draw.text((CARD_X + CARD_W - bw - 10, CUR_Y + 20), result_badge, fill=border_color, font=get_font(True, 12))
        
    CUR_Y += card_h + 20

# Step 1
draw_step(
    "08:30",
    "1",
    "Murojaat yuborish (Ish vaqtidan oldin)",
    "Talaba uyidan turib smartfonda Telegram bot orqali ariza jo'natadi",
    [
        "• Sardor HEMIS login-paroli bilan kiradi (tizim 2 kunlik xavfsiz token beradi, anketa avtomat yuklanadi).",
        "• 'O'qish joyidan ma'lumotnoma' xizmatini tanlaydi va sababini ko'rsatib arizani jo'natadi.",
        "• Tizim javobi: 'Arizangiz qabul qilindi (#ID-4082). Registrator ofisi 09:00 dan e'tiboran ko'rib chiqadi'."
    ],
    "Avto-qabul: 24/7",
    "#38BDF8"
)

# Step 2
draw_step(
    "09:15",
    "2",
    "Ofis boshlig'i arizani yo'naltiradi",
    "Boshliq arizani ko'rib, mas'ul ijrochiga biriktiradi",
    [
        "• Ofis boshlig'i kompyuterida yangi tushgan #ID-4082 arizani ochadi va toifasini tasdiqlaydi.",
        "• Arizani Front bo'limi xodimi Malika Karimovaga biriktiradi (12h/24h nazorat taymeri boshlanadi).",
        "• Ijro muddati: 1 ish kuni (24 soat). Tizimda 'Yashil zona' (normal ijro) taymeri yurishni boshlaydi."
    ],
    "SLA: 24 soat",
    "#818CF8"
)

# Step 3
draw_step(
    "11:45",
    "3",
    "Ijro va QR-kodli rasmiy PDF berish",
    "Xodim arizani hal etadi va himoyalangan hujjatni biriktiradi",
    [
        "• Malika HEMIS bazasidan ma'lumotnomani shakllantirib, unikal QR-kod va elektron muhr qo'yadi.",
        "• Tizimga PDF yuklanishi bilanoq Sardorning Telegramiga tayyor rasmiy hujjat yetib boradi.",
        "• Tizimda talaba uchun 72 soatlik tasdiqlash seansi ochiladi (24h va 48h da bot eslatma beradi)."
    ],
    "QR-kodli PDF",
    "#FBBF24"
)

# Step 4
draw_step(
    "12:10",
    "4",
    "Tasdiqlash va xolisona baholash",
    "Talaba natijani tekshirib tasdiqlaydi va xizmat sifatiga baho beradi",
    [
        "• Sardor telefonida rasmiy PDF ni ochadi, QR-kod borligini tekshiradi va ishxonasiga taqdim etadi.",
        "• Telegram botdagi '[Tasdiqlandi]' tugmasini bosib, xodimga 5 yulduzli a'lo baho qo'yadi.",
        "• Natija: Murojaat bor-yo'g'i 3 soat 40 daqiqada 100% shaffof, sarson-sargardonliksiz yopildi."
    ],
    "3 soat 40 daqiqada yopildi",
    "#34D399"
)

# --- 4. NIZOLI HOLAT (AGAR TALABA NOROZI BO'LSA) ---
draw.rectangle([PAD_X, CUR_Y, W - PAD_X, CUR_Y + 130], fill="#1C2541", outline="#F43F5E", width=2)
draw.rectangle([PAD_X, CUR_Y, PAD_X + 6, CUR_Y + 130], fill="#F43F5E")

draw.text((PAD_X + 25, CUR_Y + 14), "AGAR TALABA NOROZI BO'LSACHI? (E'TIROZ VA ESKALATSIYA MEXANIZMI)", fill="#FB7185", font=get_font(True, 16))
draw.text((PAD_X + 25, CUR_Y + 42), "• Talaba '[E'tiroz]' tugmasini bossa, ariza xodimga qaytmaydi (o'zaro ziddiyat va bosimni oldini olish uchun)!", fill="#E2E8F0", font=get_font(False, 13))
draw.text((PAD_X + 25, CUR_Y + 68), "• Ariza to'g'ridan-to'g'ri Ofis boshlig'iga boradi. Agar boshliq bilan ham kelishuv bo'lmasa, O'quv prorektoriga o'tadi.", fill="#E2E8F0", font=get_font(False, 13))
draw.text((PAD_X + 25, CUR_Y + 94), "• O'quv ishlari bo'yicha prorektorning qarori qat'iy va yakuniy hisoblanadi. Shu bilan masala to'liq arxivlanadi.", fill="#E2E8F0", font=get_font(False, 13))

CUR_Y += 150

# --- 5. ESKI USUL VS YANGI TIZIM (RAHBARIYAT UCHUN NATIJA) ---
draw.text((PAD_X, CUR_Y), "RAHBARIYAT UCHUN ANIQ FOYDA: ESKI USUL VA YANGI TIZIM TAQQOSI", fill="#E2E8F0", font=get_font(True, 18))
CUR_Y += 30

col_w = (W - PAD_X * 2 - 20) // 2

# Eski usul
draw.rectangle([PAD_X, CUR_Y, PAD_X + col_w, CUR_Y + 150], fill="#1C2541", outline="#475569")
draw.rectangle([PAD_X, CUR_Y, PAD_X + col_w, CUR_Y + 30], fill="#334155")
draw.text((PAD_X + 15, CUR_Y + 6), "ESKI AN'ANAVIY USUL (MUAMMO)", fill="#F87171", font=get_font(True, 13))
draw.text((PAD_X + 15, CUR_Y + 42), "• Ijro vaqti: 3 kundan 10 kungacha navbat va sarsonlik", fill="#94A3B8", font=get_font(False, 12))
draw.text((PAD_X + 15, CUR_Y + 66), "• Xarajat: Talaba viloyatdan yo'l bosib kelishga majbur (150+ km)", fill="#94A3B8", font=get_font(False, 12))
draw.text((PAD_X + 15, CUR_Y + 90), "• Qog'oz sarfi: 3-4 varaq qog'oz, pechat va imzo kutish", fill="#94A3B8", font=get_font(False, 12))
draw.text((PAD_X + 15, CUR_Y + 114), "• Nazorat: Qog'oz stolda yo'qolib qolishi, javobgarlik yo'qligi", fill="#94A3B8", font=get_font(False, 12))

# Yangi tizim
draw.rectangle([PAD_X + col_w + 20, CUR_Y, W - PAD_X, CUR_Y + 150], fill="#1C2541", outline="#059669")
draw.rectangle([PAD_X + col_w + 20, CUR_Y, W - PAD_X, CUR_Y + 30], fill="#065F46")
draw.text((PAD_X + col_w + 35, CUR_Y + 6), "YANGI ELEKTRON TIZIM (YECHIM)", fill="#34D399", font=get_font(True, 13))
draw.text((PAD_X + col_w + 35, CUR_Y + 42), "• Ijro vaqti: Bor-yo'g'i 3 soat 40 daqiqa (3-5 barobar tez)", fill="#E2E8F0", font=get_font(True, 12))
draw.text((PAD_X + col_w + 35, CUR_Y + 66), "• Xarajat: 0 so'm, uydan turib Telegram botda hal etildi", fill="#E2E8F0", font=get_font(True, 12))
draw.text((PAD_X + col_w + 35, CUR_Y + 90), "• Qog'oz sarfi: 0 qog'oz (QR-kodli rasmiy elektron PDF)", fill="#E2E8F0", font=get_font(True, 12))
draw.text((PAD_X + col_w + 35, CUR_Y + 114), "• Nazorat: 100% raqamli audit log, xodimning shaffof KPI reytingi", fill="#E2E8F0", font=get_font(True, 12))

CUR_Y += 170

# Save
out_path = "c:\\Users\\Veon Admin\\Downloads\\Roffice_Appeal\\Hayotiy_Keys_Asl_Nusxa_A4.png"
img.save(out_path, "PNG", quality=95)
print(f"Flawless case study poster created at: {out_path}")
