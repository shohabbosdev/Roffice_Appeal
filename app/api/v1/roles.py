from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, require_permission
from app.models import User, UserRole, CustomRole
from app.schemas import (
    RoleOut,
    RoleCreate,
    RoleUpdate,
    StaffPermissionsOverride,
)
from app.core.permissions import PERMISSIONS_CATALOG
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get("/catalog", response_model=Dict[str, Any])
async def get_permissions_catalog(
    current_user: User = Depends(get_current_user),
):
    """Tizimdagi barcha ruxsatlar katalogini kategoriyalarga ajratilgan holda qaytaradi."""
    return {"catalog": PERMISSIONS_CATALOG}


@router.get("", response_model=List[RoleOut])
async def list_roles(
    current_user: User = Depends(require_permission("users:view", "users:manage", "*")),
    db: AsyncSession = Depends(get_db),
):
    """Barcha rollar ro'yxatini qaytaradi."""
    return await RoleService.get_roles(db)


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Yangi rol yaratish (Faqat Bosh Administrator)."""
    new_role = await RoleService.create_role(db, data)
    return RoleOut(
        id=new_role.id,
        code=new_role.code,
        name=new_role.name,
        description=new_role.description,
        permissions=new_role.permissions or [],
        is_system=new_role.is_system,
        is_immutable=new_role.is_immutable,
        user_count=0,
        created_at=new_role.created_at,
        updated_at=new_role.updated_at,
    )


@router.get("/{role_id}", response_model=RoleOut)
async def get_role(
    role_id: int,
    current_user: User = Depends(require_permission("users:view", "users:manage", "*")),
    db: AsyncSession = Depends(get_db),
):
    """Muayyan rolni ID bo'yicha olish."""
    role = await RoleService.get_role_by_id(db, role_id)
    roles = await RoleService.get_roles(db)
    target = next((r for r in roles if r["id"] == role.id), None)
    return target or role


@router.put("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Rol nomi, tavsifi va ruxsatlarini yangilash (Faqat Bosh Administrator)."""
    updated_role = await RoleService.update_role(db, role_id, data)
    roles = await RoleService.get_roles(db)
    target = next((r for r in roles if r["id"] == updated_role.id), None)
    return target or updated_role


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Maxsus rolni o'chirish (Faqat Bosh Administrator, shablon rollar o'chirilmaydi)."""
    await RoleService.delete_role(db, role_id)
    return {"message": "Rol muvaffaqiyatli o'chirildi."}


@router.post("/seed-defaults")
async def seed_defaults(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Birlamchi shablon rollarni qayta tiklash/yaratish."""
    await RoleService.seed_default_roles(db)
    return {"message": "Birlamchi shablon rollar muvaffaqiyatli sinxronlandi."}


@router.get("/staff/{user_id}/permissions")
async def get_staff_permissions(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Xodimning bazaviy rol ruxsatlari, individual ustamalari va yakuniy huquqlarini ko'rish."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi."
        )

    role_res = await db.execute(select(CustomRole).where(CustomRole.code == user.role.value))
    role_obj = role_res.scalar_one_or_none()
    role_permissions = role_obj.permissions if role_obj else []

    effective = await RoleService.get_effective_permissions(user, db)

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role.value,
        "role_permissions": role_permissions,
        "custom_permissions": user.custom_permissions or [],
        "effective_permissions": effective,
    }


@router.put("/staff/{user_id}/permissions")
async def update_staff_permissions(
    user_id: int,
    data: StaffPermissionsOverride,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Xodimga individual ruxsatlar ustamasini biriktirish."""
    user = await RoleService.update_staff_custom_permissions(
        db, user_id, data.custom_permissions
    )
    effective = await RoleService.get_effective_permissions(user, db)
    return {
        "message": "Xodim huquqlari muvaffaqiyatli saqlandi.",
        "user_id": user.id,
        "custom_permissions": user.custom_permissions or [],
        "effective_permissions": effective,
    }
