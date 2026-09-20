import pytest
import pytest_asyncio
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models import (
    User, UserRole, Department, DepartmentType, Service, ResolutionMode,
    EmployeeKPITarget
)

settings.TESTING = True
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_test_data(test_db: AsyncSession):
    # Department
    dept = Department(
        name="Talabalarga xizmat ko'rsatish sektori",
        code="FRONT_STUDENT",
        dept_type=DepartmentType.FRONT_OFFICE,
        window_number="1-darcha"
    )
    test_db.add(dept)
    await test_db.flush()

    # Service
    service = Service(
        department_id=dept.id,
        code="SVC-001",
        title="Talabalik to'g'risida ma'lumotnoma",
        description="Elektron ma'lumotnoma",
        kpi_points=4,
        sla_hours=24,
        resolution_mode=ResolutionMode.BOTH
    )
    test_db.add(service)
    await test_db.flush()

    # Users
    student = User(
        username="test_student",
        hashed_password=hash_password("Pass123!"),
        full_name="Alisher Navoiy",
        role=UserRole.STUDENT,
        hemis_student_id="HEMIS-TEST-01",
        education_form="Sirtqi"
    )
    staff = User(
        username="test_staff",
        hashed_password=hash_password("Pass123!"),
        full_name="Malika Xodima",
        role=UserRole.FRONT_STAFF,
        department_id=dept.id
    )
    staff2 = User(
        username="test_staff2",
        hashed_password=hash_password("Pass123!"),
        full_name="Jasur Xodim",
        role=UserRole.BACK_STAFF,
        department_id=dept.id
    )
    head = User(
        username="test_head",
        hashed_password=hash_password("Pass123!"),
        full_name="Akrom Boshliq",
        role=UserRole.OFFICE_HEAD
    )
    prorektor = User(
        username="test_prorektor",
        hashed_password=hash_password("Pass123!"),
        full_name="Sherzod Prorektor",
        role=UserRole.VICE_RECTOR
    )
    admin = User(
        username="admin",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Tizim Ma'muri",
        role=UserRole.ADMIN
    )

    test_db.add_all([student, staff, staff2, head, prorektor, admin])
    await test_db.flush()

    # Staff KPI target
    kpi = EmployeeKPITarget(
        employee_id=staff.id,
        period="2026-09",
        target_points=150,
        completed_points=0,
        penalty_points=0,
        total_appeals_completed=0,
        total_appointments_completed=0,
        average_rating=5.0,
        kpi_percentage=0.0
    )
    test_db.add(kpi)
    await test_db.commit()

    return {
        "dept": dept,
        "service": service,
        "student": student,
        "staff": staff,
        "staff2": staff2,
        "head": head,
        "prorektor": prorektor,
        "admin": admin
    }


def create_token_for_user(user_id: int, role: UserRole) -> str:
    return create_access_token(
        data={"sub": str(user_id), "role": role.value},
        expires_delta=timedelta(hours=2)
    )
