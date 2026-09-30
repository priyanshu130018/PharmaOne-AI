"""Script to verify Supabase database connection and canonical data."""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv("backend/.env")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set!")
        sys.exit(1)
        
    print(f"Connecting to database: {db_url[:35]}...")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        print("\n--- 1. Database & User ---")
        curr = await conn.execute(text("SELECT current_database(), current_user;"))
        print("Connected as:", curr.all())

        print("\n--- 2. Public Tables ---")
        tables = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"))
        table_names = [r[0] for r in tables.fetchall()]
        print(f"Total tables: {len(table_names)}")
        print("Tables:", table_names)

        print("\n--- 3. Canonical Records Verification ---")
        # DEV-2026-018
        dev = await conn.execute(text("SELECT reference, title, status FROM deviations WHERE reference = 'DEV-2026-018'"))
        rows = dev.all()
        assert len(rows) > 0, "DEV-2026-018 missing!"
        print("DEV-2026-018:", rows[0])

        # INV-2026-012
        inv = await conn.execute(text("SELECT reference, title, status FROM investigations WHERE reference = 'INV-2026-012'"))
        rows = inv.all()
        assert len(rows) > 0, "INV-2026-012 missing!"
        print("INV-2026-012:", rows[0])

        # RCA-2026-012
        rca = await conn.execute(text("SELECT reference, root_cause_summary FROM root_cause_analyses WHERE reference = 'RCA-2026-012'"))
        rows = rca.all()
        assert len(rows) > 0, "RCA-2026-012 missing!"
        print("RCA-2026-012:", rows[0])

        # CAPA-2026-009
        capa = await conn.execute(text("SELECT reference, title, status FROM capas WHERE reference = 'CAPA-2026-009'"))
        rows = capa.all()
        assert len(rows) > 0, "CAPA-2026-009 missing!"
        print("CAPA-2026-009:", rows[0])

        # EFF-2026-009
        eff = await conn.execute(text("SELECT reference, status, plan_description FROM effectiveness_checks WHERE reference = 'EFF-2026-009'"))
        rows = eff.all()
        assert len(rows) > 0, "EFF-2026-009 missing!"
        print("EFF-2026-009:", rows[0])

        # Batches API-2026-041 through API-2026-046
        batches = await conn.execute(text("SELECT batch_number, status, product_name FROM batches WHERE batch_number LIKE 'API-2026-04%' ORDER BY batch_number"))
        batch_rows = batches.all()
        print(f"Batches ({len(batch_rows)}):", [b[0] for b in batch_rows])
        batch_nums = {b[0] for b in batch_rows}
        for expected in ["API-2026-041", "API-2026-042", "API-2026-043", "API-2026-044", "API-2026-045", "API-2026-046"]:
            assert expected in batch_nums, f"{expected} missing!"

        # BR-2026-041
        br = await conn.execute(text("SELECT reference, status FROM batch_releases WHERE reference = 'BR-2026-041'"))
        rows = br.all()
        assert len(rows) > 0, "BR-2026-041 missing!"
        print("BR-2026-041:", rows[0])

        # COM-2026-003
        com = await conn.execute(text("SELECT reference, product_name, description FROM complaints WHERE reference = 'COM-2026-003'"))
        rows = com.all()
        assert len(rows) > 0, "COM-2026-003 missing!"
        print("COM-2026-003:", rows[0])

        # RM-2026-001
        rm = await conn.execute(text("SELECT lot_number, name FROM raw_materials WHERE lot_number = 'RM-2026-001'"))
        rows = rm.all()
        assert len(rows) > 0, "RM-2026-001 missing!"
        print("RM-2026-001:", rows[0])

        # ChemCorp Company & Supplier
        comp = await conn.execute(text("SELECT name, status FROM companies WHERE name = 'ChemCorp'"))
        rows = comp.all()
        assert len(rows) > 0, "ChemCorp company missing!"
        print("Company ChemCorp:", rows[0])

        sup = await conn.execute(text("SELECT name, status FROM suppliers WHERE name = 'ChemCorp'"))
        rows = sup.all()
        assert len(rows) > 0, "ChemCorp supplier missing!"
        print("Supplier ChemCorp:", rows[0])

    await engine.dispose()
    print("\n>>> ALL CANONICAL RECORDS FOUND AND VERIFIED IN SUPABASE POSTGRESQL! <<<")

if __name__ == "__main__":
    asyncio.run(check())
