from fastapi import APIRouter

from app.api.v1 import deviations, health, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(deviations.router)
api_router.include_router(reports.router)
