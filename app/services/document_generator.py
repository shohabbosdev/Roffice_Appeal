import os
import io
import math
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import qrcode
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from app.core.config import settings
from app.models import User, Appeal, Appointment

logger = logging.getLogger(__name__)

CERT_DIR = Path(settings.UPLOAD_DIR) / "certificates"


class NumberedCanvas(canvas.Canvas):
    """Rasmiy blanka uchun fon, ramka, suv belgisi va kolontitul chizuvchi canvas."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_official_frame(num_pages)
            super().showPage()
        super().save()

    def draw_official_frame(self, page_count: int):
        self.saveState()
        width, height = A4

        # 1. Bezakli tashqi va ichki ramkalar
        self.setStrokeColor(colors.HexColor("#1e3a8a"))  # Deep Blue
        self.setLineWidth(1.5)
        self.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)

        self.setStrokeColor(colors.HexColor("#93c5fd"))  # Light Blue border
        self.setLineWidth(0.5)
        self.rect(1.35 * cm, 1.35 * cm, width - 2.7 * cm, height - 2.7 * cm)

        # 2. Suv belgisi (Watermark) — markazda 45 gradus burchak ostida xira yozuv
        self.saveState()
        self.setFont("Helvetica-Bold", 32)
        self.setFillColor(colors.HexColor("#f1f5f9"))
        self.translate(width / 2.0, height / 2.0)
        self.rotate(45)
        self.drawCentredString(0, 40, "O'zMU JF REGISTRATOR OFISI")
        self.drawCentredString(0, -10, "RASMIY ELEKTRON HUJJAT")
        self.restoreState()

        # 3. Pastki qism (Footer)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(1.5 * cm, 1.45 * cm, "Mirzo Ulug'bek nomidagi O'zMU Jizzax filiali — Registrator ofisi axborot tizimi")
        self.drawRightString(width - 1.5 * cm, 1.45 * cm, f"Sahifa {self._pageNumber} / {page_count}")

        self.restoreState()


class DocumentGenerator:
    """Rasmiy QR-kodli elektron ma'lumotnomalar va blankalar generatori."""

    @staticmethod
    def ensure_cert_dir() -> Path:
        CERT_DIR.mkdir(parents=True, exist_ok=True)
        return CERT_DIR

    @classmethod
    def generate_qr_code_image(cls, url: str) -> io.BytesIO:
        """Berilgan havola uchun yuqori aniqlikdagi QR-kod tasvirini xotirada (BytesIO) hosil qiladi."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f172a", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer

    @classmethod
    def get_public_verification_url(cls, qr_hash: str) -> str:
        """Ochiq tekshirish sahifasi to'liq havolasi."""
        base_url = "https://jbnuu.uz/roffice-appeal"
        return f"{base_url}/verify/{qr_hash}"

    @classmethod
    def generate_student_reference_pdf(
        cls,
        student: User,
        qr_hash: str,
        ticket_number: Optional[str] = None,
        purpose: str = "Talab qilingan joyga taqdim etish uchun"
    ) -> str:
        """
        Talabalik to'g'risida rasmiy elektron ma'lumotnoma (O'qish joyidan ma'lumotnoma)
        PDF faylini yaratadi va saqlaydi.
        """
        cls.ensure_cert_dir()
        now = datetime.now(timezone.utc)
        current_year = now.year
        doc_code = f"JBNUU-RO-{current_year}-{qr_hash[:8].upper()}"
        filename = f"malumotnoma_{student.username}_{qr_hash[:10]}.pdf"
        file_path = CERT_DIR / filename

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm
        )

        styles = getSampleStyleSheet()

        # Shaxsiy stillar
        header_title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a")
        )
        header_sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569")
        )
        doc_title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=10
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#1e293b")
        )
        table_label_style = ParagraphStyle(
            'TableLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155")
        )
        table_val_style = ParagraphStyle(
            'TableVal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0f172a")
        )

        story = []

        # 1. Rasmiy blanka sarlavhasi
        story.append(Paragraph("O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI", header_title_style))
        story.append(Paragraph("MIRZO ULUG'BEK NOMIDAGI O'ZBEKISTON MILLIY UNIVERSITETI JIZZAX FILIALI", header_title_style))
        story.append(Paragraph("REGISTRATOR OFISI BO'LIMI", header_title_style))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("130100, Jizzax shahri, Sh.Rashidov shox ko'chasi, 259-uy • Tel: (72) 226-46-52 • Web: https://jbnuu.uz", header_sub_style))
        story.append(Spacer(1, 4 * mm))

        # Ajratuvchi chiziq
        line_table = Table([['']], colWidths=[17.5 * cm])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor("#1e3a8a")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 5 * mm))

        # Sana va ro'yxat raqami
        meta_table = Table([
            [
                Paragraph(f"<b>Sana:</b> {now.strftime('%d.%m.%Y')}", body_style),
                Paragraph(f"<b>Hujjat kodi:</b> <font color='#1e3a8a'>{doc_code}</font>", ParagraphStyle('R', parent=body_style, alignment=TA_RIGHT))
            ]
        ], colWidths=[8.7 * cm, 8.8 * cm])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6 * mm))

        # Hujjat nomi
        story.append(Paragraph("MA'LUMOTNOMA", doc_title_style))
        story.append(Spacer(1, 3 * mm))

        # Kirish matni
        p_intro = (
            f"Ushbu ma'lumotnoma berildiki, haqiqatdan ham <b>{student.full_name}</b> "
            f"Mirzo Ulug'bek nomidagi O'zbekiston Milliy universiteti Jizzax filiali talabasi hisoblanadi."
        )
        story.append(Paragraph(p_intro, body_style))
        story.append(Spacer(1, 4 * mm))

        # Talabaning akademik parametrlari jadvali
        table_data = [
            [Paragraph("F.I.SH.:", table_label_style), Paragraph(student.full_name, table_val_style)],
            [Paragraph("HEMIS talaba ID:", table_label_style), Paragraph(student.hemis_student_id or student.username, table_val_style)],
            [Paragraph("Fakultet:", table_label_style), Paragraph(student.faculty or "Mavjud emas", table_val_style)],
            [Paragraph("Ta'lim yo'nalishi / Mutaxassisligi:", table_label_style), Paragraph(student.specialty or "Axborot tizimlari va texnologiyalari", table_val_style)],
            [Paragraph("Guruh:", table_label_style), Paragraph(student.group_name or "Mavjud emas", table_val_style)],
            [Paragraph("Bosqich (kurs):", table_label_style), Paragraph(f"{student.course or 1}-bosqich", table_val_style)],
            [Paragraph("Ta'lim shakli:", table_label_style), Paragraph(student.education_form or "Kunduzgi", table_val_style)],
            [Paragraph("Ta'lim turi:", table_label_style), Paragraph(student.education_type or "Bakalavriat", table_val_style)],
            [Paragraph("O'quv yili:", table_label_style), Paragraph(f"{current_year-1}/{current_year}-o'quv yili", table_val_style)],
            [Paragraph("Berilish maqsadi:", table_label_style), Paragraph(purpose, table_val_style)],
        ]

        akademik_table = Table(table_data, colWidths=[6.0 * cm, 11.5 * cm])
        akademik_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(akademik_table)
        story.append(Spacer(1, 6 * mm))

        # Huquqiy eslatma
        legal_text = (
            "<i>Mazkur ma'lumotnoma O'zbekiston Respublikasi Vazirlar Mahkamasining tegishli qarorlari "
            "hamda Oliy ta'lim, fan va innovatsiyalar vazirligining 73-sonli Namunaviy Nizomi asosida "
            "Registrator ofisi axborot tizimi orqali elektron shakllantirildi va qonuniy kuchga ega.</i>"
        )
        story.append(Paragraph(legal_text, ParagraphStyle('Legal', parent=body_style, fontSize=8, leading=11, textColor=colors.HexColor("#475569"))))
        story.append(Spacer(1, 8 * mm))

        # QR kod va elektron muhr (Shtamp) bloki
        verify_url = cls.get_public_verification_url(qr_hash)
        qr_stream = cls.generate_qr_code_image(verify_url)
        qr_img = RLImage(qr_stream, width=3.2 * cm, height=3.2 * cm)

        stamp_text = (
            "<b>O'ZBEKISTON MILLIY UNIVERSITETI JIZZAX FILIALI</b><br/>"
            "<b>REGISTRATOR OFISI BO'LIMI</b><br/>"
            "Elektron raqamli tasdiqlangan<br/>"
            f"<b>Sana:</b> {now.strftime('%d.%m.%Y %H:%M')}<br/>"
            f"<b>Verifikatsiya kodi:</b> {qr_hash[:16]}..."
        )

        stamp_box = Table([
            [Paragraph(f"<font color='#1e3a8a'>●</font> <b>Elektron Tasdiq (e-Stamp)</b>", table_label_style)],
            [Paragraph(stamp_text, ParagraphStyle('Stamp', parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor("#1e3a8a")))]
        ], colWidths=[7.0 * cm])
        stamp_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#2563eb")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        qr_desc = (
            "<b>Haqiqiyligini tekshirish:</b><br/>"
            "QR-kodni smartfon kamerasi orqali skaner qiling yoki quyidagi rasmiy manzil orqali tekshiring:<br/>"
            f"<font color='#2563eb'><u>{verify_url}</u></font>"
        )

        footer_table = Table([
            [stamp_box, qr_img, Paragraph(qr_desc, ParagraphStyle('QRDesc', parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor("#334155")))]
        ], colWidths=[7.2 * cm, 3.4 * cm, 6.9 * cm])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ]))

        story.append(footer_table)

        # PDF hujjatni tuzish
        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info(f"Talabalik ma'lumotnomasi muvaffaqiyatli yaratildi: {file_path}")

        return f"/uploads/certificates/{filename}"

    @classmethod
    def generate_appeal_resolution_pdf(
        cls,
        appeal: Appeal,
        student: User,
        staff: Optional[User],
        qr_hash: str
    ) -> str:
        """
        Murojaat bo'yicha rasmiy ijro blankasi (Ijro xulosasi) PDF hujjatini yaratadi.
        """
        cls.ensure_cert_dir()
        now = datetime.now(timezone.utc)
        filename = f"ijro_blankasi_{appeal.ticket_number}_{qr_hash[:10]}.pdf"
        file_path = CERT_DIR / filename

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm
        )

        styles = getSampleStyleSheet()

        header_title_style = ParagraphStyle(
            'HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a")
        )
        doc_title_style = ParagraphStyle(
            'DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=15, leading=19, alignment=TA_CENTER, textColor=colors.HexColor("#1e3a8a"), spaceAfter=10
        )
        body_style = ParagraphStyle(
            'Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, alignment=TA_JUSTIFY, textColor=colors.HexColor("#1e293b")
        )
        label_style = ParagraphStyle(
            'Label', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor("#334155")
        )
        val_style = ParagraphStyle(
            'Val', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor("#0f172a")
        )

        story = []

        # 1. Sarlavha
        story.append(Paragraph("O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI", header_title_style))
        story.append(Paragraph("MIRZO ULUG'BEK NOMIDAGI O'ZMU JIZZAX FILIALI REGISTRATOR OFISI", header_title_style))
        story.append(Spacer(1, 3 * mm))

        # Ajratuvchi chiziq
        line_table = Table([['']], colWidths=[17.5 * cm])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor("#1e3a8a")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 4 * mm))

        # 2. Hujjat nomi va chipta raqami
        story.append(Paragraph("MUROJAATNING RASMIY IJRO BLANKASI", doc_title_style))
        story.append(Paragraph(f"Talon raqami: <b>{appeal.ticket_number}</b>", ParagraphStyle('Ticket', parent=doc_title_style, fontSize=11, textColor=colors.HexColor("#475569"))))
        story.append(Spacer(1, 3 * mm))

        # 3. Murojaat va talaba parametrlari
        t_data = [
            [Paragraph("Murojaatchi talaba:", label_style), Paragraph(student.full_name, val_style)],
            [Paragraph("Fakultet va guruh:", label_style), Paragraph(f"{student.faculty or '—'} / {student.group_name or '—'}", val_style)],
            [Paragraph("Xizmat turi:", label_style), Paragraph(appeal.service.title if appeal.service else "Ariza", val_style)],
            [Paragraph("Murojaat mavzusi:", label_style), Paragraph(appeal.subject, val_style)],
            [Paragraph("Murojaat yuborilgan sana:", label_style), Paragraph(appeal.created_at.strftime("%d.%m.%Y %H:%M") if appeal.created_at else "—", val_style)],
            [Paragraph("Ijrochi xodim:", label_style), Paragraph(staff.full_name if staff else "Registrator ofisi xodimi", val_style)],
            [Paragraph("Holati (Status):", label_style), Paragraph(f"<font color='#059669'><b>HAL ETILGAN (RESOLVED)</b></font>", val_style)],
        ]
        info_table = Table(t_data, colWidths=[5.5 * cm, 12.0 * cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 5 * mm))

        # 4. Murojaat matni va ijro xulosasi
        story.append(Paragraph("<b>Murojaat mazmuni:</b>", label_style))
        story.append(Paragraph(appeal.message, body_style))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("<b>Registrator ofisi rasmiy ijro xulosasi:</b>", label_style))
        res_text = appeal.resolution_text or "Murojaat Registrator ofisi tomonidan to'liq ko'rib chiqildi va ijobiy hal etildi."
        story.append(Paragraph(res_text, body_style))
        story.append(Spacer(1, 6 * mm))

        # 5. QR-kod va e-Stamp
        verify_url = cls.get_public_verification_url(qr_hash)
        qr_stream = cls.generate_qr_code_image(verify_url)
        qr_img = RLImage(qr_stream, width=3.0 * cm, height=3.0 * cm)

        stamp_text = (
            "<b>O'ZMU JIZZAX FILIALI REGISTRATOR OFISI</b><br/>"
            "Elektron tasdiqlangan hujjat<br/>"
            f"<b>Sana:</b> {now.strftime('%d.%m.%Y %H:%M')}<br/>"
            f"<b>Ijrochi:</b> {staff.full_name if staff else 'Xodim'}"
        )
        stamp_box = Table([
            [Paragraph(stamp_text, ParagraphStyle('S', parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor("#1e3a8a")))]
        ], colWidths=[7.0 * cm])
        stamp_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#2563eb")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        footer_table = Table([
            [stamp_box, qr_img, Paragraph(f"Haqiqiyligini tekshirish uchun QR-kodni skanerlang:<br/><font color='#2563eb'><u>{verify_url}</u></font>", ParagraphStyle('Q', parent=body_style, fontSize=7.5, leading=10))]
        ], colWidths=[7.2 * cm, 3.2 * cm, 7.1 * cm])
        story.append(footer_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        return f"/uploads/certificates/{filename}"
