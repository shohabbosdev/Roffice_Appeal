import io
import pytest
from httpx import AsyncClient
from app.models import User, UserRole
from app.core.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_file_upload_flow(client: AsyncClient, test_db):
    """Fayl yuklash, validatsiya va statik tarqatish testlari."""
    # 1. Foydalanuvchi yaratish
    user = User(
        username="student_upload_test",
        hashed_password=hash_password("Pass123!"),
        full_name="Fayl Yuklovchi Talaba",
        role=UserRole.STUDENT,
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ruxsatsiz urinish (401)
    no_auth_resp = await client.post("/api/v1/uploads")
    assert no_auth_resp.status_code == 401

    # 3. Noto'g'ri kengaytmadagi fayl (.exe) (400)
    bad_file = io.BytesIO(b"malicious executable code")
    bad_resp = await client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("virus.exe", bad_file, "application/octet-stream")}
    )
    assert bad_resp.status_code == 400
    assert "Faqat quyidagi formatdagi fayllar" in bad_resp.json()["detail"]

    # 4. To'g'ri PDF faylni yuklash (200)
    pdf_content = b"%PDF-1.4 ... test pdf document content ..."
    pdf_file = io.BytesIO(pdf_content)
    ok_resp = await client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("ariza_hujjat.pdf", pdf_file, "application/pdf")}
    )
    assert ok_resp.status_code == 200
    res_data = ok_resp.json()
    assert res_data["success"] is True
    assert res_data["original_name"] == "ariza_hujjat.pdf"
    assert res_data["file_url"].startswith("/uploads/")

    # 5. Yuklangan faylni GET orqali ochish / yuklab olish (200)
    download_resp = await client.get(res_data["file_url"])
    assert download_resp.status_code == 200
    assert download_resp.content == pdf_content
