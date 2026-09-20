import re
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException, status
from app.core.config import settings


class HemisClient:
    """HEMIS Axborot tizimi API integratsiya mijozi (https://student.jbnuu.uz/rest/v1)."""

    @classmethod
    async def login(cls, login: str | int, password: str) -> Dict[str, str]:
        """Talaba login va parolini HEMIS serveriga yuborib token va refresh_token olish."""
        url = f"{settings.HEMIS_BASE_URL}/auth/login"
        payload = {
            "login": str(login).strip(),
            "password": password
        }

        try:
            async with httpx.AsyncClient(timeout=settings.HEMIS_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"accept": "application/json", "Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data and "token" in data["data"]:
                        return {
                            "token": data["data"]["token"],
                            "refresh_token": data["data"].get("refresh_token")
                        }
                elif response.status_code == 401:
                    err_msg = "HEMIS login yoki parol noto'g'ri."
                    try:
                        err_data = response.json()
                        if err_data.get("error"):
                            err_msg = err_data.get("error")
                    except Exception:
                        pass
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err_msg)

                # Boshqa xatolik holatlarida
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"HEMIS serveri javob bermadi yoki xatolik qaytardi (HTTP {response.status_code})."
                )

        except httpx.RequestError as exc:
            # Tarmoq ulanish xatoligi yoki offline rejim
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HEMIS serveri bilan bog'lanib bo'lmadi: {str(exc)}"
            )

    @classmethod
    async def refresh_token(cls, refresh_token: str) -> Dict[str, Any]:
        """X-Refresh-Token orqali talaba sessiyasini yangilash."""
        url = f"{settings.HEMIS_BASE_URL}/auth/refresh-token"
        headers = {
            "accept": "application/json",
            "X-Refresh-Token": refresh_token
        }

        try:
            async with httpx.AsyncClient(timeout=settings.HEMIS_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        return data["data"]

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token yaroqsiz yoki muddati o'tgan. Iltimos qaytadan login qiling."
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"HEMIS serveriga ulanishda xatolik: {str(exc)}"
            )

    # Oddiy va xavfsiz TTL kesh (5 daqiqa)
    _profile_cache: Dict[str, Any] = {}
    CACHE_TTL_SECONDS = 300

    @classmethod
    async def get_me(cls, access_token: str) -> Dict[str, Any]:
        """HEMIS talaba profil ma'lumotlarini olish (TTL kesh bilan)."""
        import time
        now = time.time()

        # Keshni tekshirish
        if access_token in cls._profile_cache:
            ts, cached_data = cls._profile_cache[access_token]
            if now - ts < cls.CACHE_TTL_SECONDS:
                return cached_data

        url = f"{settings.HEMIS_BASE_URL}/account/me"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        try:
            async with httpx.AsyncClient(timeout=settings.HEMIS_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        profile_data = data["data"]
                        cls._profile_cache[access_token] = (now, profile_data)
                        return profile_data

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="HEMIS sessiyasi tugagan yoki token yaroqsiz. Iltimos qaytadan login qiling."
                    )

                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"HEMIS tizimi profil ma'lumotlarini taqdim eta olmadi (Status kodi: {response.status_code})."
                )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Universitet HEMIS tizimi vaqtincha javob bermayapti (Server Timeout). Iltimos, bir ozdan so'ng qayta urinib ko'ring."
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Universitet HEMIS tizimi bilan aloqa o'rnatib bo'lmadi: {str(exc)}"
            )

    @staticmethod
    def filter_safe_academic_profile(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Shaxsga doir maxfiy ma'lumotlarni qat'iy chetlatish (PII Protection):
        - PASSPORT / PINFL (`passport_pin`) SAQLANMAYDI!
        - TUG'ILGAN SANA (`birth_date`) SAQLANMAYDI!
        - YASHASH MANZILI (`address`, `province`, `district`) SAQLANMAYDI!
        - IJTIMOIY TOIFA (`socialCategory`, `povertyLevel`) SAQLANMAYDI!
        
        Faqat Registrator ofisi xizmati uchun zarur bo'lgan akademik maydonlar olinadi.
        """
        # Kurs raqamini aniqlash
        course_num: Optional[int] = None
        level_obj = raw_data.get("level")
        if isinstance(level_obj, dict):
            level_name = str(level_obj.get("name", ""))
            match = re.search(r"(\d+)", level_name)
            if match:
                course_num = int(match.group(1))
            elif level_obj.get("code") and str(level_obj.get("code")).isdigit():
                course_num = int(str(level_obj.get("code"))[-1])

        # Fakultet
        faculty_name = None
        fac_obj = raw_data.get("faculty")
        if isinstance(fac_obj, dict):
            faculty_name = fac_obj.get("name")

        # Guruh
        group_name = None
        grp_obj = raw_data.get("group")
        if isinstance(grp_obj, dict):
            group_name = grp_obj.get("name")

        # Mutaxassislik
        spec_name = None
        spec_obj = raw_data.get("specialty")
        if isinstance(spec_obj, dict):
            spec_name = spec_obj.get("name")

        # Ta'lim turi va shakli
        edu_type = None
        type_obj = raw_data.get("educationType")
        if isinstance(type_obj, dict):
            edu_type = type_obj.get("name")

        edu_form = None
        form_obj = raw_data.get("educationForm")
        if isinstance(form_obj, dict):
            edu_form = form_obj.get("name")

        return {
            "hemis_student_id": str(raw_data.get("student_id_number", "")),
            "full_name": raw_data.get("full_name", ""),
            "faculty": faculty_name,
            "group_name": group_name,
            "course": course_num,
            "specialty": spec_name,
            "education_type": edu_type,
            "education_form": edu_form,
            "email": raw_data.get("email"),
            "phone": raw_data.get("phone")
        }
