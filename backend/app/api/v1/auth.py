"""Authentication API endpoints (Supabase Auth bridge)."""

import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user, record_audit_event, _get_supabase_client
from app.core.enums import AuditAction
from app.db.session import get_session
from app.models.org import Company, CompanyMembership, Profile, Site

logger = logging.getLogger("app.api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    company_id: str
    company_name: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: Optional[int] = None
    user: UserResponse


class DemoUserItem(BaseModel):
    name: str
    email: str
    company: str
    role: str
    department: str


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_session),
):
    """Authenticate with Supabase Auth using email and password."""
    email_clean = payload.email.lower().strip()
    supabase_client = _get_supabase_client()

    try:
        auth_res = supabase_client.auth.sign_in_with_password({
            "email": email_clean,
            "password": payload.password,
        })
    except Exception as e:
        logger.warning("Failed login attempt for %s: %s", email_clean, e)
        # Record failed login attempt if profile exists
        prof_res = await db.execute(select(Profile).where(Profile.email == email_clean))
        prof = prof_res.scalar_one_or_none()
        if prof:
            await record_audit_event(
                db,
                action=AuditAction.ACCESS_DENIED,
                entity_type="user",
                entity_id=prof.id,
                user_id=prof.id,
                meta={"reason": "invalid_credentials"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not auth_res.user or not auth_res.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: no session returned",
        )

    import uuid
    user_id = uuid.UUID(auth_res.user.id)

    # Load Profile & Active Membership from DB
    stmt = (
        select(Profile, CompanyMembership, Company, Site)
        .join(CompanyMembership, CompanyMembership.user_id == Profile.id)
        .join(Company, Company.id == CompanyMembership.company_id)
        .outerjoin(Site, Site.id == CompanyMembership.site_id)
        .where(Profile.id == user_id, CompanyMembership.is_active.is_(True))
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        prof_res = await db.execute(select(Profile).where(Profile.id == user_id))
        prof = prof_res.scalar_one_or_none()
        if not prof:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not initialized",
            )
        if prof.status != "active":
            await record_audit_event(
                db,
                action=AuditAction.ACCESS_DENIED,
                entity_type="user",
                entity_id=user_id,
                user_id=user_id,
                meta={"reason": "account_inactive"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive or disabled",
            )
        await record_audit_event(
            db,
            action=AuditAction.ACCESS_DENIED,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            meta={"reason": "no_active_company_membership"},
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
            meta={"reason": "account_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled",
        )

    # Log successful LOGIN in audit trail
    await record_audit_event(
        db,
        action=AuditAction.LOGIN,
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        company_id=company.id,
        meta={"email": profile.email, "role": membership.role},
    )

    return LoginResponse(
        access_token=auth_res.session.access_token,
        token_type="bearer",
        expires_at=auth_res.session.expires_at,
        user=UserResponse(
            id=str(profile.id),
            email=profile.email,
            full_name=profile.full_name,
            employee_id=profile.employee_id,
            department=profile.department,
            job_title=profile.job_title,
            company_id=str(company.id),
            company_name=company.name,
            site_id=str(site.id) if site else None,
            site_name=site.name if site else None,
            role=membership.role,
        ),
    )


@router.post("/logout")
async def logout(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Log out user and record audit event."""
    await record_audit_event(
        db,
        action=AuditAction.LOGOUT,
        entity_type="user",
        entity_id=current_user.user_id,
        user_id=current_user.user_id,
        company_id=current_user.company_id,
        meta={"email": current_user.email},
    )
    return {"status": "ok", "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve currently authenticated user profile and membership."""
    return UserResponse(
        id=str(current_user.user_id),
        email=current_user.email,
        full_name=current_user.full_name,
        employee_id=current_user.employee_id,
        department=current_user.department,
        job_title=current_user.job_title,
        company_id=str(current_user.company_id),
        company_name=current_user.company_name,
        site_id=str(current_user.site_id) if current_user.site_id else None,
        site_name=current_user.site_name,
        role=current_user.role,
    )


@router.get("/demo-users", response_model=List[DemoUserItem])
async def list_demo_users():
    """Public helper listing predefined demo user."""
    return [
        {
            "name": "Priyanshu",
            "email": "priyanshu@gmail.com",
            "company": "Vasundha Pharma Chem Limited",
            "role": "QA Manager",
            "department": "Quality Assurance",
        },
    ]
