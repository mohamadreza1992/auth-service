from fastapi import APIRouter

from app.api.health import router as health_router
from app.features.auth.router import router as auth_router
from app.features.sessions.router import router as sessions_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(sessions_router)
