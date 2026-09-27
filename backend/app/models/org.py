import uuid
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Company(Base, TimestampMixin):
    """Pharmaceutical enterprise organization."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)

    sites: Mapped[List["Site"]] = relationship("Site", back_populates="company", cascade="all, delete-orphan")
    memberships: Mapped[List["CompanyMembership"]] = relationship("CompanyMembership", back_populates="company", cascade="all, delete-orphan")


class Site(Base, TimestampMixin):
    """Manufacturing plant or laboratory site belonging to a company."""

    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)

    company: Mapped["Company"] = relationship("Company", back_populates="sites")


class Profile(Base, TimestampMixin):
    """User profile record mapped 1-to-1 with Supabase auth.users.id."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # Populated from Supabase user.id
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    employee_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)

    memberships: Mapped[List["CompanyMembership"]] = relationship("CompanyMembership", back_populates="profile", cascade="all, delete-orphan")


class CompanyMembership(Base, TimestampMixin):
    """User membership and role in an organization."""

    __tablename__ = "company_memberships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(48), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["Profile"] = relationship("Profile", back_populates="memberships")
    company: Mapped["Company"] = relationship("Company", back_populates="memberships")
    site: Mapped[Optional["Site"]] = relationship("Site")
