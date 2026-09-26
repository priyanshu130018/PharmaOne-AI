from datetime import datetime

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    status: str = Field(..., examples=["ok"])
    environment: str
    version: str


class ReadinessStatus(BaseModel):
    status: str = Field(..., examples=["ready", "degraded"])
    database: str = Field(..., examples=["connected", "unavailable"])
    checked_at: datetime


class ErrorResponse(BaseModel):
    detail: str
