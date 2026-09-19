import pytest
import os
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole, Appeal, AppealStatus, Service, ResolutionMode
from app.core.security import hash_password
from app.services.document_generator import DocumentGenerator, CERT_DIR
from app.services.appeal_service import AppealService
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_document_generator_pdf_creation(test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    qr_hash = "TESTQRHASH123456"

    # 1. Talabalik ma'lumotnomasi PDF generatsiyasi
    pdf_rel_path = DocumentGenerator.generate_student_reference_pdf(
        student=student,
        qr_hash=qr_hash,
        ticket_number="TALAB-TEST-001"
    )
    assert pdf_rel_path.startswith("/uploads/certificates/")
    assert pdf_rel_path.endswith(".pdf")

    full_path = Path(".") / pdf_rel_path.lstrip("/")
    assert full_path.exists()
    assert full_path.stat().st_size > 1000

    # PDF fayl baytlarini tekshirish
    with open(full_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"

    # 2. QR kod stream generatsiyasi
    qr_stream = DocumentGenerator.generate_qr_code_image("https://jbnuu.uz/roffice-appeal/verify/TEST")
    assert qr_stream.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"

    # Tozalash
    try:
        full_path.unlink(missing_ok=True)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_public_verification_api_flow(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    service = seed_test_data["service"]
    staff = seed_test_data["staff"]

    qr_hash = "VERIFY_TEST_HASH_99"

    # Ariza yaratamiz
    appeal = Appeal(
        ticket_number="APP-VERIFY-001",
        student_id=student.id,
        service_id=service.id,
        assigned_staff_id=staff.id,
        status=AppealStatus.RESOLVED,
        subject="Ma'lumotnoma so'rovi",
        message="Ish joyimga taqdim etish uchun ma'lumotnoma kerak.",
        resolution_text="Ma'lumotnoma rasmiylashtirildi.",
        qr_hash=qr_hash
    )
    test_db.add(appeal)
    await test_db.flush()

    # PDF yaratib unga biriktiramiz
    pdf_url = DocumentGenerator.generate_student_reference_pdf(student=student, qr_hash=qr_hash)
    appeal.result_file_url = pdf_url
    await test_db.commit()

    # 1. Ochiq verifikatsiya endpointi (autentifikatsiyasiz) -> 200 OK
    resp = await client.get(f"/api/v1/verify/{qr_hash}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["verified"] is True
    assert data["qr_hash"] == qr_hash
    assert data["student"]["full_name"] == student.full_name
    assert "JBNUU-RO-" in data["doc_code"]
    assert data["resolution"]["pdf_url"] == pdf_url

    # 2. Asl PDF faylni yuklab olish -> 200 OK
    resp_dl = await client.get(f"/api/v1/verify/{qr_hash}/download")
    assert resp_dl.status_code == 200
    assert resp_dl.headers.get("content-type") == "application/pdf"
    assert len(resp_dl.content) > 1000

    # 3. Noto'g'ri hash uchun -> 404 NOT FOUND
    resp_fake = await client.get("/api/v1/verify/NON_EXISTING_HASH_000")
    assert resp_fake.status_code == 404

    # 4. Statik HTML verifikatsiya sahifasi -> 200 OK
    resp_page = await client.get(f"/verify/{qr_hash}")
    assert resp_page.status_code == 200
    assert "text/html" in resp_page.headers.get("content-type", "")

    # Tozalash
    try:
        (Path(".") / pdf_url.lstrip("/")).unlink(missing_ok=True)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_appeal_resolve_auto_generates_pdf(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    student = seed_test_data["student"]
    staff = seed_test_data["staff"]
    service = seed_test_data["service"]

    # Yangi ariza yaratamiz
    appeal = await AppealService.create_appeal(
        db=test_db,
        student_id=student.id,
        service_id=service.id,
        subject="O'qish joyidan ma'lumotnoma olish",
        message="Menga rasmiy QR ma'lumotnoma bering."
    )

    # Xodim arizani hal etadi, lekin fayl yuklamaydi (result_file_url=None)
    resolved_appeal = await AppealService.resolve_appeal(
        db=test_db,
        appeal_id=appeal.id,
        staff_id=staff.id,
        resolution_text="Talabalik ma'lumotnomasi elektron tasdiqlandi.",
        result_file_url=None
    )

    # Tizim avtomatik ravishda PDF yaratgan bo'lishi kerak
    assert resolved_appeal.status == AppealStatus.RESOLVED
    assert resolved_appeal.qr_hash is not None
    assert resolved_appeal.result_file_url is not None
    assert resolved_appeal.result_file_url.endswith(".pdf")

    pdf_file = Path(".") / resolved_appeal.result_file_url.lstrip("/")
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000

    # Tozalash
    try:
        pdf_file.unlink(missing_ok=True)
    except Exception:
        pass
