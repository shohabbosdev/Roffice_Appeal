import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserRole
from app.core.security import hash_password
from app.services.backup_service import BackupService, BACKUP_DIR
from tests.conftest import create_token_for_user


@pytest.mark.asyncio
async def test_system_metrics_endpoint(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    head = seed_test_data["head"]
    student = seed_test_data["student"]

    # 1. Unauthenticated -> 401
    resp = await client.get("/api/v1/system/metrics")
    assert resp.status_code == 401

    # 2. Student (unauthorized role) -> 403
    student_token = create_token_for_user(student.id, student.role)
    resp = await client.get("/api/v1/system/metrics", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403

    # 3. Office Head (unauthorized role, system is admin only) -> 403
    head_token = create_token_for_user(head.id, head.role)
    resp = await client.get("/api/v1/system/metrics", headers={"Authorization": f"Bearer {head_token}"})
    assert resp.status_code == 403

    # 4. Administrator -> 200 OK
    admin = seed_test_data["admin"]
    admin_token = create_token_for_user(admin.id, admin.role)
    resp = await client.get("/api/v1/system/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()

    assert "status" in data
    assert "environment" in data
    assert "cpu" in data
    assert "ram" in data
    assert "disk" in data
    assert "database" in data
    assert data["database"]["total_users"] >= 5


@pytest.mark.asyncio
async def test_backup_flow_and_rbac(client: AsyncClient, test_db: AsyncSession, seed_test_data):
    # Admin yaratamiz
    admin = User(
        username="test_admin_backup",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Tizim Administratori",
        role=UserRole.ADMIN
    )
    test_db.add(admin)
    await test_db.commit()

    student = seed_test_data["student"]
    student_token = create_token_for_user(student.id, student.role)
    admin_token = create_token_for_user(admin.id, admin.role)

    # 1. Student zaxira yarata olmaydi -> 403
    resp = await client.post("/api/v1/system/backups", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403

    # 2. Admin yangi zaxira yaratadi -> 200
    resp = await client.post("/api/v1/system/backups", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    backup_info = resp.json()
    assert backup_info["success"] is True
    assert "backup_roffice_" in backup_info["filename"]
    assert backup_info["filename"].endswith(".tar.gz")
    assert backup_info["size_bytes"] > 0

    filename = backup_info["filename"]

    # 3. Zaxiralar ro'yxatini olish
    resp = await client.get("/api/v1/system/backups", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    backups_list = resp.json()
    assert len(backups_list) >= 1
    assert any(b["filename"] == filename for b in backups_list)

    # 4. Zaxirani yuklab olish
    resp = await client.get(f"/api/v1/system/backups/{filename}/download", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.headers.get("content-type") in ["application/gzip", "application/x-gzip", "application/octet-stream"]
    assert len(resp.content) > 0

    # 5. Path Traversal urinishi -> 400
    resp = await client.get("/api/v1/system/backups/../../etc/passwd/download", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code in [400, 404]

    # 6. Mavjud bo'lmagan zaxira -> 404
    resp = await client.get("/api/v1/system/backups/backup_roffice_99999999_999999.tar.gz/download", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404

    # Tozalash
    try:
        (BACKUP_DIR / filename).unlink(missing_ok=True)
    except Exception:
        pass
