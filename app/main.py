from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_v1_router
from app.services.telegram_bot import run_telegram_bot_poller
from app.services.sla_reminder import run_sla_reminder_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe migrations for existing SQLite database
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN assigned_duties TEXT DEFAULT NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN telegram_chat_id INTEGER DEFAULT NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100) DEFAULT NULL"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN telegram_connected_at DATETIME DEFAULT NULL"))
        except Exception:
            pass

    # Start background tasks
    bot_task = asyncio.create_task(run_telegram_bot_poller())
    sla_task = asyncio.create_task(run_sla_reminder_loop())
    yield
    bot_task.cancel()
    sla_task.cancel()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Mirzo Ulug'bek nomidagi O'zbekiston Milliy universiteti Jizzax filiali "
        "registrator ofisi talabalar murojaatlari, elektron navbat ('Kelib hal etish') "
        "va xodimlar KPI samaradorligini avtomatlashtirilgan baholash tizimi backend platformasi."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8087",
        "http://127.0.0.1:8087",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:3000",
        "https://student.jbnuu.uz"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files directory if present
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount Uploads directory for documents and attachments
uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# API Routers
app.include_router(api_v1_router)


@app.get("/", tags=["Asosiy"])
async def root(request: Request):
    """
    Asosiy sahifa: Brauzer orqali kirilganda autentifikatsiya oynasini (login) ochadi.
    API orqali (Accept: application/json) so'rov yuborilganda tizim metama'lumotlarini qaytaradi.
    """
    accept_header = request.headers.get("accept", "")
    login_path = Path(__file__).resolve().parent / "static" / "login.html"

    if ("text/html" in accept_header or "*/*" in accept_header) and "application/json" not in accept_header:
        if login_path.exists():
            return FileResponse(str(login_path), media_type="text/html")

    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "filial": "O'zMU Jizzax filiali",
        "version": "1.0.0",
        "login": "/login",
        "student_portal": "/student",
        "staff_portal": "/staff",
        "docs": "/docs",
        "working_hours": f"{settings.WORK_START_HOUR}:00 - {settings.WORK_END_HOUR}:00",
        "lunch_break": f"{settings.LUNCH_START_HOUR}:00 - {settings.LUNCH_END_HOUR}:00"
    }


@app.get("/login", tags=["Asosiy"])
async def get_login():
    """Autentifikatsiya oynasi (talaba HEMIS va xodimlar kirishi)."""
    login_path = Path(__file__).resolve().parent / "static" / "login.html"
    if login_path.exists():
        return FileResponse(str(login_path), media_type="text/html")
    return JSONResponse(status_code=404, content={"message": "Login HTML fayli topilmadi"})


@app.get("/student", tags=["Asosiy"])
async def get_student_portal():
    """Faqat talabalar uchun shaxsiy kabinet (ariza berish, navbat taloni, mening arizalarim)."""
    student_path = Path(__file__).resolve().parent / "static" / "student.html"
    if student_path.exists():
        return FileResponse(str(student_path), media_type="text/html")
    return JSONResponse(status_code=404, content={"message": "Student HTML fayli topilmadi"})


@app.get("/staff", tags=["Asosiy"])
async def get_staff_portal():
    """Registrator ofisi xodimlari va rahbariyat ish stoli (monitoring, cheklovlar, KPI, navbat)."""
    staff_path = Path(__file__).resolve().parent / "static" / "staff.html"
    if staff_path.exists():
        return FileResponse(str(staff_path), media_type="text/html")
    return JSONResponse(status_code=404, content={"message": "Staff HTML fayli topilmadi"})


@app.get("/portal", tags=["Asosiy"])
async def get_portal():
    """Umumiy taqdimot portali (showcase prototip)."""
    portal_path = Path(__file__).resolve().parent / "static" / "portal.html"
    if portal_path.exists():
        return FileResponse(str(portal_path), media_type="text/html")
    return JSONResponse(status_code=404, content={"message": "Portal HTML fayli topilmadi"})


@app.get("/api/info", tags=["Asosiy"])
async def api_info():
    """Tizim konfiguratsiyasi va ish vaqti parametrlari."""
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "filial": "O'zMU Jizzax filiali",
        "version": "1.0.0",
        "docs": "/docs",
        "working_hours": f"{settings.WORK_START_HOUR}:00 - {settings.WORK_END_HOUR}:00",
        "lunch_break": f"{settings.LUNCH_START_HOUR}:00 - {settings.LUNCH_END_HOUR}:00"
    }


@app.get("/health", tags=["Asosiy"])
async def health_check():
    return {"status": "healthy"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


