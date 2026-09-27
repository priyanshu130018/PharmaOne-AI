"""FastAPI authentication and authorization dependencies for Supabase Auth.

Enforces:
- Bearer token extraction and cryptographic/API validation.
- Profile and company membership resolution from PostgreSQL.
- Company data isolation (derived from authenticated membership, never trusted from client).
- Role-based access control (Admin, QA Manager, Production User, QC User).
- Immutable audit event logging (LOGIN, LOGOUT, ACCESS_DENIED).
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.core.config import get_settings
from app.core.enums import AuditAction
from app.db.session import get_session
from app.models.audit import AuditEvent
from app.models.org import Company, CompanyMembership, Profile, Site

logger = logging.getLogger("app.auth")
security_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Canonical authenticated user context resolved from Supabase token & database."""

    user_id: uuid.UUID
    email: str
    full_name: str
    employee_id: Optional[str]
    department: Optional[str]
    job_title: Optional[str]
    company_id: uuid.UUID
    company_name: str
    site_id: Optional[uuid.UUID]
    site_name: Optional[str]
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "Admin"


async def record_audit_event(
    db: AsyncSession,
    action: AuditAction,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    company_id: Optional[uuid.UUID] = None,
    meta: Optional[dict] = None,
) -> AuditEvent:
    """Helper to record an immutable audit event."""
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        company_id=company_id,
        meta=meta or {},
    )
    db.add(event)
    await db.flush()
    return event


def _get_supabase_client():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_session),
) -> AuthenticatedUser:
    """Validate Supabase JWT and load user profile with active company membership."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    settings = get_settings()
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None

    # Handle test mock tokens for offline/unit testing
    if settings.ENVIRONMENT == "test" and token.startswith("test-token-"):
        # e.g. "test-token-priyanshu" or "test-token-admin"
        target_name = token.replace("test-token-", "").lower()
        stmt_prof = select(Profile).where(Profile.email.ilike(f"%{target_name}%"))
        res_prof = await db.execute(stmt_prof)
        test_prof = res_prof.scalar_one_or_none()
        if test_prof:
            user_id = test_prof.id
            email = test_prof.email
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid test token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # Validate with Supabase Auth
        try:
            supabase_client = _get_supabase_client()
            user_resp = supabase_client.auth.get_user(token)
            if not user_resp or not user_resp.user:
                raise ValueError("No user returned from token")
            user_id = uuid.UUID(user_resp.user.id)
            email = user_resp.user.email
        except Exception as e:
            logger.warning("Supabase token validation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Load Profile from PostgreSQL
    stmt = (
        select(Profile, CompanyMembership, Company, Site)
        .join(CompanyMembership, CompanyMembership.user_id == Profile.id)
        .join(Company, Company.id == CompanyMembership.company_id)
        .outerjoin(Site, Site.id == CompanyMembership.site_id)
        .where(Profile.id == user_id, CompanyMembership.is_active.is_(True))
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        # Check if profile exists at all
        prof_res = await db.execute(select(Profile).where(Profile.id == user_id))
        prof = prof_res.scalar_one_or_none()
        if not prof:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not found in system",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if prof.status != "active":
            await record_audit_event(
                db,
                action=AuditAction.ACCESS_DENIED,
                entity_type="user",
                entity_id=user_id,
                user_id=user_id,
                meta={"reason": "inactive_account"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive or disabled",
            )
        # Profile exists but no active membership
        await record_audit_event(
            db,
            action=AuditAction.ACCESS_DENIED,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            meta={"reason": "missing_active_company_membership"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active company membership",
        )

    profile, membership, company, site = row

    if profile.status != "active":
        await record_audit_event(
            db,
            action=AuditAction.ACCESS_DENIED,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            company_id=company.id,
            meta={"reason": "inactive_account"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled",
        )

    return AuthenticatedUser(
        user_id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        employee_id=profile.employee_id,
        department=profile.department,
        job_title=profile.job_title,
        company_id=company.id,
        company_name=company.name,
        site_id=site.id if site else None,
        site_name=site.name if site else None,
        role=membership.role,
    )


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory checking that the authenticated user has one of the allowed roles."""

    async def _role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied for user %s (role: %s) to endpoint requiring %s",
                user.email,
                user.role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role permissions. Required: {', '.join(allowed_roles)}",
            )
        return user

    return _role_checker


require_admin = require_role("Admin")
