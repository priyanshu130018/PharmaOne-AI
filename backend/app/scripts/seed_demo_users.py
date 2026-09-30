"""Idempotent provisioning script for single Priyanshu demo user and cleanup of old demo accounts.

Usage:
    python -m app.scripts.seed_demo_users

Creates / updates the Priyanshu demo user in Supabase Auth via Service Role API,
removes obsolete demo accounts, and synchronizes the profile, company, site,
and membership in PostgreSQL.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select, update
from supabase import create_client

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models.org import Company, CompanyMembership, Profile, Site

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo_users")

OLD_DEMO_EMAILS = [
    "rahul@gmail.com",
    "aman@gmail.com",
    "aryan@gmail.com",
    "rohit@gmail.com",
    "kartik@gmail.com",
]

PRIYANSHU_DEMO = {
    "email": "priyanshu@gmail.com",
    "password": "123456789",
    "full_name": "Priyanshu",
    "employee_id": "DEMO-001",
    "department": "Quality Assurance",
    "job_title": "QA Manager",
    "company": "Vasundha Pharma Chem Limited",
    "site": "Demo Manufacturing Site",
    "role": "QA Manager",
    "status": "active",
}


async def seed_users():
    settings = get_settings()
    logger.info("Connecting to Supabase Auth via Service Role API...")
    supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    # 1. Fetch existing Supabase auth users to avoid duplicates and identify old demo users
    existing_supabase_users = {}
    page = 1
    per_page = 50
    while True:
        try:
            user_list = supabase_client.auth.admin.list_users(page=page, per_page=per_page)
            if not user_list:
                break
            for u in user_list:
                existing_supabase_users[u.email.lower()] = u
            if len(user_list) < per_page:
                break
            page += 1
        except Exception as e:
            logger.warning("Error fetching Supabase auth user page %d: %s", page, e)
            break

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        # 2. Clean up old demo accounts (Rahul, Aman, Aryan, Rohit, Kartik)
        for old_email in OLD_DEMO_EMAILS:
            if old_email in existing_supabase_users:
                old_auth_user = existing_supabase_users[old_email]
                try:
                    supabase_client.auth.admin.delete_user(str(old_auth_user.id))
                    logger.info("Deleted obsolete demo user from Supabase Auth: %s", old_email)
                except Exception as e:
                    logger.warning("Could not delete %s from Supabase Auth: %s", old_email, e)

            # Inactivate in PostgreSQL database
            stmt_old = select(Profile).where(Profile.email == old_email)
            res_old = await db.execute(stmt_old)
            old_profile = res_old.scalar_one_or_none()
            if old_profile:
                old_profile.status = "disabled"
                # Deactivate all company memberships
                await db.execute(
                    update(CompanyMembership)
                    .where(CompanyMembership.user_id == old_profile.id)
                    .values(is_active=False)
                )
                logger.info("Deactivated PostgreSQL profile and memberships for: %s", old_email)

        # 3. Ensure the single Priyanshu demo user exists in Supabase Auth
        p_email = PRIYANSHU_DEMO["email"].lower()
        p_password = PRIYANSHU_DEMO["password"]
        p_user_id: uuid.UUID

        if p_email in existing_supabase_users:
            auth_user = existing_supabase_users[p_email]
            p_user_id = uuid.UUID(auth_user.id)
            logger.info("Found existing Priyanshu user in Supabase Auth: %s (id: %s)", p_email, p_user_id)
            try:
                supabase_client.auth.admin.update_user_by_id(
                    str(p_user_id),
                    {
                        "password": p_password,
                        "email_confirm": True,
                        "user_metadata": {"full_name": PRIYANSHU_DEMO["full_name"]},
                    },
                )
                logger.info("Updated Priyanshu password and confirmed email in Supabase Auth")
            except Exception as e:
                logger.warning("Could not update Priyanshu user in Supabase Auth: %s", e)
        else:
            logger.info("Creating Priyanshu demo user in Supabase Auth: %s", p_email)
            create_resp = supabase_client.auth.admin.create_user(
                {
                    "email": p_email,
                    "password": p_password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": PRIYANSHU_DEMO["full_name"]},
                }
            )
            p_user_id = uuid.UUID(create_resp.user.id)
            logger.info("Created Priyanshu demo user in Supabase Auth: %s (id: %s)", p_email, p_user_id)

        # 4. Company record (Vasundha Pharma Chem Limited)
        stmt_comp = select(Company).where(Company.name == PRIYANSHU_DEMO["company"])
        res_comp = await db.execute(stmt_comp)
        company = res_comp.scalar_one_or_none()
        if not company:
            company = Company(name=PRIYANSHU_DEMO["company"], status="active")
            db.add(company)
            await db.flush()
            logger.info("Created Company: %s", company.name)
        else:
            company.status = "active"
            await db.flush()

        # 5. Site record (Demo Manufacturing Site)
        stmt_site = select(Site).where(
            Site.company_id == company.id,
            Site.name == PRIYANSHU_DEMO["site"],
        )
        res_site = await db.execute(stmt_site)
        site = res_site.scalar_one_or_none()
        if not site:
            site = Site(company_id=company.id, name=PRIYANSHU_DEMO["site"], status="active")
            db.add(site)
            await db.flush()
            logger.info("Created Site: %s for %s", site.name, company.name)
        else:
            site.status = "active"
            await db.flush()

        # 6. Profile record for Priyanshu
        stmt_prof = select(Profile).where(Profile.id == p_user_id)
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()
        if not profile:
            # Also check if profile exists with this email under different UUID
            stmt_email = select(Profile).where(Profile.email == p_email)
            res_email = await db.execute(stmt_email)
            prof_by_email = res_email.scalar_one_or_none()
            if prof_by_email:
                await db.delete(prof_by_email)
                await db.flush()

            profile = Profile(
                id=p_user_id,
                email=p_email,
                full_name=PRIYANSHU_DEMO["full_name"],
                employee_id=PRIYANSHU_DEMO["employee_id"],
                department=PRIYANSHU_DEMO["department"],
                job_title=PRIYANSHU_DEMO["job_title"],
                status="active",
            )
            db.add(profile)
            await db.flush()
            logger.info("Created Profile: %s (%s)", profile.full_name, profile.email)
        else:
            profile.email = p_email
            profile.full_name = PRIYANSHU_DEMO["full_name"]
            profile.employee_id = PRIYANSHU_DEMO["employee_id"]
            profile.department = PRIYANSHU_DEMO["department"]
            profile.job_title = PRIYANSHU_DEMO["job_title"]
            profile.status = "active"
            await db.flush()
            logger.info("Updated Profile: %s (%s)", profile.full_name, profile.email)

        # 7. Ensure exactly ONE active Company Membership
        # Inactivate any stale memberships for Priyanshu
        await db.execute(
            update(CompanyMembership)
            .where(
                CompanyMembership.user_id == p_user_id,
                CompanyMembership.company_id != company.id,
            )
            .values(is_active=False)
        )

        stmt_mem = select(CompanyMembership).where(
            CompanyMembership.user_id == p_user_id,
            CompanyMembership.company_id == company.id,
        )
        res_mem = await db.execute(stmt_mem)
        membership = res_mem.scalar_one_or_none()
        if not membership:
            membership = CompanyMembership(
                user_id=p_user_id,
                company_id=company.id,
                site_id=site.id,
                role=PRIYANSHU_DEMO["role"],
                is_active=True,
            )
            db.add(membership)
            await db.flush()
            logger.info("Assigned Membership: %s -> %s as %s", PRIYANSHU_DEMO["full_name"], company.name, PRIYANSHU_DEMO["role"])
        else:
            membership.site_id = site.id
            membership.role = PRIYANSHU_DEMO["role"]
            membership.is_active = True
            await db.flush()
            logger.info("Ensured Active Membership: %s -> %s as %s", PRIYANSHU_DEMO["full_name"], company.name, PRIYANSHU_DEMO["role"])

        await db.commit()
        logger.info("Successfully finished provisioning Priyanshu demo account and cleaning up old demo users!")

    from app.db.session import dispose_engine
    await dispose_engine()


def main():
    asyncio.run(seed_users())


if __name__ == "__main__":
    main()
