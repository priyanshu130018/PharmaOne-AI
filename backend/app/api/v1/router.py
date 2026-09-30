from fastapi import APIRouter

from app.api.v1 import auth, deviations, health, qms, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(deviations.router)
api_router.include_router(reports.router)
api_router.include_router(qms.router)
api_router.include_router(qms.router, prefix="/qms")
