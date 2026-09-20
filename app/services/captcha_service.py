import uuid
import random
import hashlib
import html
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.models import CaptchaChallenge

# Kichik harflar va o'qilishi oson raqamlar (adashmaslik uchun 0, o, 1, l, i olib tashlangan)
CAPTCHA_CHARS = "abcdefhjkmnprstuvwxyz23456789"
CAPTCHA_TTL_SECONDS = 120  # 2 daqiqa
FONT_FAMILIES = ["Arial, sans-serif", "Courier New, monospace", "Verdana, sans-serif", "Georgia, serif"]
COLORS = ["#38bdf8", "#34d399", "#818cf8", "#fbbf24", "#f472b6", "#a78bfa", "#2dd4bf"]


class CaptchaService:
    """Backend darajasida bir martalik xavfsiz Captcha generatsiyasi va verifikatsiyasi."""

    @classmethod
    def _hash_code(cls, code: str) -> str:
        """Kichik harflardagi kodni maxfiy salt bilan SHA-256 hashlaydi."""
        salt = getattr(settings, "SECRET_KEY", "roffice_captcha_salt_2026")
        clean_code = code.strip().lower()
        return hashlib.sha256(f"{clean_code}:{salt}".encode("utf-8")).hexdigest()

    @classmethod
    def _generate_svg(cls, text: str) -> str:
        """
        Shovqin chiziqlari, to'lqinlar, rangli gradientlar va burilgan
        kichik harflar bilan xavfsiz SVG tasvirini chizadi.
        """
        width = 160
        height = 50

        # Shovqin chiziqlari
        lines_svg = []
        for _ in range(4):
            x1 = random.randint(5, 40)
            y1 = random.randint(5, height - 5)
            x2 = random.randint(width - 40, width - 5)
            y2 = random.randint(5, height - 5)
            stroke_color = random.choice(COLORS)
            stroke_width = random.uniform(1.2, 2.0)
            lines_svg.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-opacity="0.55" />'
            )

        # Shovqin doirachalari
        dots_svg = []
        for _ in range(25):
            cx = random.randint(5, width - 5)
            cy = random.randint(5, height - 5)
            r = random.uniform(1.0, 2.2)
            fill_color = random.choice(COLORS)
            dots_svg.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill_color}" fill-opacity="0.35" />'
            )

        # Harflarni alohida burchaklar ostida joylashtirish
        chars_svg = []
        char_count = len(text)
        step = (width - 30) / char_count

        for i, ch in enumerate(text):
            x = 18 + int(i * step) + random.randint(-2, 3)
            y = random.randint(32, 38)
            rotate_angle = random.randint(-22, 22)
            font_size = random.randint(22, 27)
            fill = random.choice(COLORS)
            font_family = random.choice(FONT_FAMILIES)

            # Harf SVG tegi
            chars_svg.append(
                f'<text x="{x}" y="{y}" fill="{fill}" font-size="{font_size}" font-family="{font_family}" '
                f'font-weight="bold" transform="rotate({rotate_angle}, {x}, {y})" '
                f'letter-spacing="2">{html.escape(ch)}</text>'
            )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'style="background: #090d16; border-radius: 12px; border: 1px solid #1e293b; user-select: none;">'
            f'<rect width="{width}" height="{height}" fill="#090d16" rx="12"/>'
            f'{"".join(dots_svg)}'
            f'{"".join(lines_svg)}'
            f'{"".join(chars_svg)}'
            f'</svg>'
        )
        return svg

    @classmethod
    async def create_challenge(cls, db: AsyncSession) -> Dict[str, str]:
        """
        Yangi bir martalik Captcha yaratadi va bazaga saqlaydi.
        Ochiq matn mijozga aslo qaytarilmaydi!
        """
        # Eskirgan captchalarni tozalash
        now = datetime.now(timezone.utc)
        try:
            await db.execute(delete(CaptchaChallenge).where(CaptchaChallenge.expires_at < now))
        except Exception:
            pass

        # 4 ta tasodifiy kichik belgi
        raw_code = "".join(random.choices(CAPTCHA_CHARS, k=4)).lower()
        hashed = cls._hash_code(raw_code)

        challenge_id = str(uuid.uuid4())
        expires_at = now + timedelta(seconds=CAPTCHA_TTL_SECONDS)

        challenge = CaptchaChallenge(
            id=challenge_id,
            hashed_code=hashed,
            created_at=now,
            expires_at=expires_at,
            is_used=False
        )
        db.add(challenge)
        await db.commit()

        svg_content = cls._generate_svg(raw_code)

        return {
            "captcha_id": challenge_id,
            "captcha_svg": svg_content
        }

    @classmethod
    async def verify_challenge(
        cls,
        db: AsyncSession,
        captcha_id: Optional[str],
        user_code: Optional[str]
    ) -> bool:
        """
        Foydalanuvchi kiritgan kodni tekshiradi.
        Bir marta tekshirilgach, darhol bazadan o'chiriladi (bir martalik kafolat).
        """
        if not captcha_id or not str(captcha_id).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Xavfsizlik tekshiruvi: Captcha kodi kiritilishi shart."
            )

        if not user_code or not str(user_code).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rasmdagi kichik harflardan iborat kodni kiriting."
            )

        clean_id = str(captcha_id).strip()
        challenge = await db.get(CaptchaChallenge, clean_id)

        now = datetime.now(timezone.utc)

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha topilmadi yoki muddati o'tgan. Iltimos, yangilang."
            )

        if challenge.is_used:
            # Replay attack oldini olish
            await db.delete(challenge)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ushbu captcha allaqachon ishlatilgan. Yangi captcha oling."
            )

        if challenge.expires_at < now:
            await db.delete(challenge)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha muddati o'tgan (2 daqiqa). Yangisini oling."
            )

        # Darhol bir martalik qilib bazadan o'chiramiz
        await db.delete(challenge)
        await db.commit()

        # Kiritilgan kodni qat'iy kichik harflarda solishtiramiz
        input_hash = cls._hash_code(user_code)
        if input_hash != challenge.hashed_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha kodi noto'g'ri kiritildi. Iltimos, qaytadan urinib ko'ring."
            )

        return True
