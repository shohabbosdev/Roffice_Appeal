from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import Service, Department, DepartmentType, ResolutionMode, User, UserRole
from app.schemas import (
    ServiceOut, ServiceCreate, ServiceUpdate,
    DepartmentOut, DepartmentCreate, DepartmentUpdate,
    MyServicesResponse
)
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/services", tags=["Xizmatlar va bo'limlar katalogi"])


# ===================== BO'LIMLAR (DEPARTMENTS) CRUD =====================

@router.get("/departments", response_model=List[DepartmentOut], summary="Registrator ofisi sohalari/bo'limlari ro'yxati")
async def get_departments(
    dept_type: Optional[DepartmentType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Nizomda belgilangan asosiy sohalar (Front va Back office) ro'yxati."""
    query = select(Department).where(Department.is_active == True)
    if dept_type:
        query = query.where(Department.dept_type == dept_type)
    query = query.order_by(Department.id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED, summary="Yangi bo'lim/soha yaratish (Admin)")
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(Department).where(Department.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ushbu bo'lim kodi mavjud.")

    dept = Department(
        name=data.name,
        code=data.code,
        dept_type=data.dept_type,
        window_number=data.window_number,
        is_active=True
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut, summary="Bo'limni tahrirlash (Admin)")
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bo'lim topilmadi.")

    if data.name is not None:
        dept.name = data.name
    if data.code is not None:
        dept.code = data.code
    if data.dept_type is not None:
        dept.dept_type = data.dept_type
    if data.window_number is not None:
        dept.window_number = data.window_number

    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", summary="Bo'limni o'chirish / nofaol qilish (Admin)")
async def delete_department(
    dept_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bo'lim topilmadi.")

    dept.is_active = False
    await db.commit()
    return {"message": "Bo'lim muvaffaqiyatli nofaol qilindi."}


# ===================== XODIMGA BIRIKTIRILGAN XIZMATLAR =====================

@router.get("/my-services", response_model=MyServicesResponse, summary="Joriy xodimga va uning bo'limiga biriktirilgan rasmiy xizmatlar")
async def get_my_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Har bir xodim tizimga kirganda o'ziga va o'z bo'limiga biriktirilgan xizmatlarni ko'rishi:
    - Front-ofis darcha xodimi: o'z darchasi xizmatlari (ma'lumotnoma, transkript yoki to'lov-shartnoma);
    - Back-ofis mutaxassisi: o'z yo'nalishi xizmatlari (arxiv, GPA qayta hisoblash, tiklash);
    - Boshliq va Admin: barcha xizmatlar.
    """
    dept = None
    if current_user.department_id:
        dept = await db.get(Department, current_user.department_id)

    if current_user.role in [UserRole.OFFICE_HEAD, UserRole.ADMIN, UserRole.VICE_RECTOR]:
        # Rahbariyat va Admin barcha xizmatlarni ko'radi
        query = select(Service).options(selectinload(Service.department)).where(Service.is_active == True).order_by(Service.department_id, Service.id)
        result = await db.execute(query)
        services = result.scalars().all()
    elif current_user.assigned_services:
        # Xodimga aynan aniq xizmatlar biriktirilgan bo'lsa
        services = current_user.assigned_services
    elif current_user.department_id:
        # Standart holat: bo'limga biriktirilgan barcha xizmatlar
        query = select(Service).options(selectinload(Service.department)).where(Service.department_id == current_user.department_id, Service.is_active == True).order_by(Service.id)
        result = await db.execute(query)
        services = result.scalars().all()
    else:
        services = []

    return MyServicesResponse(department=dept, services=services)


# ===================== XIZMATLAR (SERVICES) CRUD =====================

@router.get("", response_model=List[ServiceOut], summary="Barcha mavjud xizmatlar ro'yxati (katalog)")
async def get_services(
    department_id: Optional[int] = Query(None, description="Soha/bo'lim bo'yicha filter"),
    dept_type: Optional[DepartmentType] = Query(None, description="Front yoki Back office bo'yicha filter"),
    resolution_mode: Optional[ResolutionMode] = Query(None, description="Hal etish usuli (ONLINE, APPOINTMENT, HYBRID)"),
    include_inactive: bool = Query(False, description="Nofaol xizmatlarni ham ko'rsatish"),
    search: Optional[str] = Query(None, description="Xizmat nomi yoki kodi bo'yicha qidiruv"),
    db: AsyncSession = Depends(get_db)
):
    """Barcha xizmatlar katalogi (KPI ballari va SLA soatlari bilan)."""
    query = select(Service).options(selectinload(Service.department))
    if not include_inactive:
        query = query.where(Service.is_active == True)

    if department_id:
        query = query.where(Service.department_id == department_id)
    if resolution_mode:
        query = query.where(Service.resolution_mode == resolution_mode)
    if dept_type:
        query = query.join(Service.department).where(Department.dept_type == dept_type)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Service.title.ilike(search_pattern)) | (Service.code.ilike(search_pattern))
        )

    query = query.order_by(Service.department_id, Service.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED, summary="Yangi xizmat turini kiritish (Boshliq / Admin)")
async def create_service(
    data: ServiceCreate,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(Service).where(Service.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ushbu xizmat kodi mavjud.")

    svc = Service(
        code=data.code,
        title=data.title,
        description=data.description,
        department_id=data.department_id,
        kpi_points=data.kpi_points,
        sla_hours=data.sla_hours,
        resolution_mode=data.resolution_mode,
        required_docs=data.required_docs,
        is_active=True
    )
    db.add(svc)
    await db.commit()
    await db.refresh(svc)

    result = await db.execute(
        select(Service).options(selectinload(Service.department)).where(Service.id == svc.id)
    )
    return result.scalar_one()


@router.get("/{service_id}", response_model=ServiceOut, summary="Xizmatning to'liq tavsifi")
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    """Tanlangan xizmat haqida batafsil ma'lumot."""
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.department))
        .where(Service.id == service_id)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bunday xizmat turi topilmadi.")
    return service


@router.put("/{service_id}", response_model=ServiceOut, summary="Xizmat reglamentini tahrirlash (Boshliq / Admin)")
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    svc = await db.get(Service, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xizmat topilmadi.")

    if data.code is not None and data.code.strip():
        new_code = data.code.strip().upper()
        if new_code != svc.code:
            existing = await db.execute(select(Service).where(Service.code == new_code))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ushbu xizmat kodi band.")
            svc.code = new_code

    if data.title is not None:
        svc.title = data.title
    if data.description is not None:
        svc.description = data.description
    if data.department_id is not None:
        svc.department_id = data.department_id
    if data.kpi_points is not None:
        svc.kpi_points = data.kpi_points
    if data.sla_hours is not None:
        svc.sla_hours = data.sla_hours
    if data.resolution_mode is not None:
        svc.resolution_mode = data.resolution_mode
    if data.required_docs is not None:
        svc.required_docs = data.required_docs
    if data.is_active is not None:
        svc.is_active = data.is_active

    await db.commit()
    result = await db.execute(
        select(Service).options(selectinload(Service.department)).where(Service.id == svc.id)
    )
    return result.scalar_one()


@router.patch("/{service_id}/toggle-active", response_model=ServiceOut, summary="Xizmatni faol/nofaol holatga o'tkazish (Boshliq / Admin)")
async def toggle_service_active(
    service_id: int,
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    svc = await db.get(Service, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xizmat topilmadi.")

    svc.is_active = not svc.is_active
    await db.commit()
    result = await db.execute(
        select(Service).options(selectinload(Service.department)).where(Service.id == svc.id)
    )
    return result.scalar_one()


@router.delete("/{service_id}", summary="Xizmatni o'chirish yoki nofaol qilish (Boshliq / Admin)")
async def delete_service(
    service_id: int,
    hard_delete: bool = Query(False, description="Agar murojaatlar bo'lmasa bazadan to'liq o'chirish"),
    current_user: User = Depends(require_role(UserRole.OFFICE_HEAD, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    svc = await db.get(Service, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xizmat topilmadi.")

    from app.models import Appeal, Appointment
    appeals_exist = (await db.execute(select(Appeal.id).where(Appeal.service_id == service_id).limit(1))).scalars().first()
    appointments_exist = (await db.execute(select(Appointment.id).where(Appointment.service_id == service_id).limit(1))).scalars().first()

    if hard_delete and not appeals_exist and not appointments_exist:
        await db.delete(svc)
        await db.commit()
        return {"message": "Xizmat tizimdan butunlay o'chirildi."}
    else:
        svc.is_active = False
        await db.commit()
        return {"message": "Xizmat nofaol (arxiv) holatiga o'tkazildi."}
