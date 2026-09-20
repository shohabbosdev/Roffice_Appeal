from typing import List, Optional, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models import CustomRole, User, UserRole
from app.schemas import RoleCreate, RoleUpdate
from app.core.permissions import (
    PERMISSIONS_CATALOG,
    DEFAULT_TEMPLATE_ROLES,
    ALL_PERMISSION_CODES,
)


class RoleService:
    @staticmethod
    async def seed_default_roles(db: AsyncSession) -> None:
        """Tizimning standart shablon rollarini bazaga kiritish (agar mavjud bo'lmasa)."""
        for tpl in DEFAULT_TEMPLATE_ROLES:
            code = tpl["code"]
            result = await db.execute(select(CustomRole).where(CustomRole.code == code))
            existing = result.scalar_one_or_none()
            if not existing:
                new_role = CustomRole(
                    code=code,
                    name=tpl["name"],
                    description=tpl["description"],
                    permissions=tpl["permissions"],
                    is_system=tpl["is_system"],
                    is_immutable=tpl["is_immutable"],
                )
                db.add(new_role)
            else:
                # Agar admin roli bo'lsa, uning o'zgarmasligi va huquqlari doim to'liq bo'lishini ta'minlash
                if existing.code == "admin":
                    existing.is_immutable = True
                    existing.is_system = True
                    existing.permissions = ["*"]
        await db.commit()

    @staticmethod
    async def get_roles(db: AsyncSession) -> List[Dict[str, Any]]:
        """Barcha rollarni biriktirilgan xodimlar soni bilan birga qaytaradi."""
        result = await db.execute(select(CustomRole).order_by(CustomRole.id.asc()))
        roles = result.scalars().all()
        
        output = []
        for r in roles:
            count_res = await db.execute(
                select(func.count()).select_from(User).where(User.role == r.code)
            )
            user_count = count_res.scalar() or 0
            output.append({
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "permissions": r.permissions or [],
                "is_system": r.is_system,
                "is_immutable": r.is_immutable,
                "user_count": user_count,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            })
        return output

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> CustomRole:
        result = await db.execute(select(CustomRole).where(CustomRole.id == role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol topilmadi."
            )
        return role

    @staticmethod
    async def get_role_by_code(db: AsyncSession, code: str) -> Optional[CustomRole]:
        result = await db.execute(select(CustomRole).where(CustomRole.code == code))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_role(db: AsyncSession, data: RoleCreate) -> CustomRole:
        clean_code = data.code.strip().lower().replace(" ", "_")
        existing = await RoleService.get_role_by_code(db, clean_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{clean_code}' kodli rol allaqachon mavjud."
            )

        # Huquqlarni tekshirish
        valid_perms = []
        for p in data.permissions:
            if p == "*" or p in ALL_PERMISSION_CODES:
                valid_perms.append(p)

        new_role = CustomRole(
            code=clean_code,
            name=data.name.strip(),
            description=data.description,
            permissions=valid_perms,
            is_system=False,
            is_immutable=False,
        )
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)
        return new_role

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, data: RoleUpdate) -> CustomRole:
        role = await RoleService.get_role_by_id(db, role_id)
        if role.is_immutable or role.code == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bosh administrator roli o'zgarmasdir va uni tahrirlash taqiqlangan."
            )

        if data.name is not None:
            role.name = data.name.strip()
        if data.description is not None:
            role.description = data.description
        if data.permissions is not None:
            valid_perms = []
            for p in data.permissions:
                if p == "*" or p in ALL_PERMISSION_CODES:
                    valid_perms.append(p)
            role.permissions = valid_perms

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> None:
        role = await RoleService.get_role_by_id(db, role_id)
        if role.is_immutable or role.code == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bosh administrator rolini o'chirish qat'iyan taqiqlangan."
            )
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tizimning standart shablon rollarini o'chirish taqiqlangan. Ruxsatlarni o'zgartirishingiz mumkin."
            )

        # Ushbu rolga foydalanuvchilar biriktirilganmi tekshirish
        count_res = await db.execute(
            select(func.count()).select_from(User).where(User.role == role.code)
        )
        attached_users = count_res.scalar() or 0
        if attached_users > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ushbu rolda {attached_users} ta foydalanuvchi mavjud. Avval ularning rolini o'zgartiring."
            )

        await db.delete(role)
        await db.commit()

    @staticmethod
    async def get_effective_permissions(user: User, db: AsyncSession) -> List[str]:
        """Foydalanuvchining roli va individual ustama huquqlaridan kelib chiqqan yakuniy huquqlarini qaytaradi."""
        # Bosh administrator har doim barcha huquqlarga ega
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role_val == "admin" or user.role == UserRole.ADMIN:
            return ["*"]

        result = await db.execute(select(CustomRole).where(CustomRole.code == role_val))
        role_obj = result.scalar_one_or_none()

        base_permissions: Set[str] = set()
        if role_obj and role_obj.permissions:
            if "*" in role_obj.permissions:
                return ["*"]
            base_permissions.update(role_obj.permissions)

        # Agar individual qo'shimcha huquqlar berilgan bo'lsa
        if user.custom_permissions:
            base_permissions.update(user.custom_permissions)

        return sorted(list(base_permissions))

    @staticmethod
    async def update_staff_custom_permissions(
        db: AsyncSession, user_id: int, custom_permissions: List[str]
    ) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Xodim topilmadi."
            )

        if user.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bosh administrator hisobiga individual ruxsat ustamalari kiritish talab etilmaydi."
            )

        valid_perms = [p for p in custom_permissions if p in ALL_PERMISSION_CODES]
        user.custom_permissions = valid_perms
        await db.commit()
        await db.refresh(user)
        return user
