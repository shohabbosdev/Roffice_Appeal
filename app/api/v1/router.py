from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.services import router as services_router
from app.api.v1.appeals import router as appeals_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.kpi import router as kpi_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(appeals_router)
api_v1_router.include_router(appointments_router)
api_v1_router.include_router(kpi_router)
api_v1_router.include_router(calendar_router)
api_v1_router.include_router(users_router)
