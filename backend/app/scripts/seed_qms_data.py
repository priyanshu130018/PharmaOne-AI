"""Idempotent seed script for Round 2 Connected QMS demo scenario:
Company: ChemCorp
Site: Bengaluru
Product: Paracetamol API
Batch: API-2026-041
Recipe: v4.2
Raw Material: Acetic Anhydride (RM-2026-001)
Manufacturing Steps: Step 1 (Charge), Step 2 (Preparation), Step 3 (Reaction - Warning)
IPC: Temperature 84 °C (Spec: 76–80 °C, OUT OF SPEC), Pressure 1.2 bar, pH 7.1, Reaction Time 2.5 hr
Deviation: DEV-2026-018 ("Reactor temperature exceeded limit", Major, Under Investigation)
Investigation: INV-2026-012 (4 tasks, 3 evidence documents)
Root Cause: RCA-2026-012 (5 Whys -> "Inadequate preventive-maintenance control for the cooling-valve actuator")
CAPA: CAPA-2026-009 (Corrective action: Replace valve actuator, Preventive action: Update PM procedure)
Effectiveness: EFF-2026-009 (5 monitored batches API-2026-042 to 046, all passed)
Batch Release: BR-2026-041 (Pending QA disposition)
Complaint: COM-2026-003 (Paracetamol API, linked to API-2026-041 & DEV-2026-018)
Supplier: ChemCorp (Approved, Medium Risk)
Plus additional quality records so dashboard metrics match:
Deviations: 12, Investigations: 4, CAPAs: 3, Batch Release: 2 pending, Complaints: 1.
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, select, update

from app.core.enums import BatchStatus, DeviationSource, DeviationStatus, DeviationType, Impact, Severity
from app.db.session import dispose_engine, get_sessionmaker
from app.models.deviation import Deviation
from app.models.org import Company, CompanyMembership, Profile, Site
from app.models.qms import (
    Batch,
    BatchRelease,
    Capa,
    CapaAction,
    Complaint,
    EffectivenessCheck,
    InProcessCheck,
    Investigation,
    InvestigationEvidence,
    InvestigationTask,
    ManufacturingStep,
    RawMaterial,
    RootCauseAnalysis,
    Supplier,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_qms_data")


async def seed_qms():
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        logger.info("Starting Connected QMS database seeding...")

        # Fast check: If canonical deviation already exists, all data is in Supabase
        check_dev = await db.execute(select(Deviation.id).where(Deviation.reference == "DEV-2026-018"))
        if check_dev.scalar_one_or_none():
            logger.info("Canonical Connected QMS demo data already exists in Supabase. No re-seeding needed.")
            return

        # 1. Ensure ChemCorp company exists
        stmt_comp = select(Company).where(Company.name == "ChemCorp")
        res_comp = await db.execute(stmt_comp)
        company = res_comp.scalar_one_or_none()
        if not company:
            company = Company(name="ChemCorp", code="CHEM", status="active")
            db.add(company)
            await db.flush()
            logger.info("Created Company: ChemCorp (%s)", company.id)
        else:
            company.status = "active"
            await db.flush()

        # 2. Ensure Bengaluru site exists for ChemCorp
        stmt_site = select(Site).where(Site.company_id == company.id, Site.name == "Bengaluru")
        res_site = await db.execute(stmt_site)
        site = res_site.scalar_one_or_none()
        if not site:
            site = Site(company_id=company.id, name="Bengaluru", code="BLR-01", status="active")
            db.add(site)
            await db.flush()
            logger.info("Created Site: Bengaluru (%s)", site.id)
        else:
            site.status = "active"
            await db.flush()

        # 3. Associate Priyanshu user profile with ChemCorp (Bengaluru site) as QA Manager
        stmt_prof = select(Profile).where(Profile.email == "priyanshu@gmail.com")
        res_prof = await db.execute(stmt_prof)
        profile = res_prof.scalar_one_or_none()
        if not profile:
            profile = Profile(
                id=uuid.UUID("d0000001-0000-0000-0000-000000000001"),
                email="priyanshu@gmail.com",
                full_name="Priyanshu",
                employee_id="DEMO-001",
                department="Quality Assurance",
                job_title="QA Manager",
                status="active",
            )
            db.add(profile)
            await db.flush()
            logger.info("Created Profile: Priyanshu (%s)", profile.id)

        # Set ChemCorp membership active for Priyanshu
        stmt_mem = select(CompanyMembership).where(
            CompanyMembership.user_id == profile.id, CompanyMembership.company_id == company.id
        )
        res_mem = await db.execute(stmt_mem)
        mem = res_mem.scalar_one_or_none()
        if not mem:
            mem = CompanyMembership(
                user_id=profile.id,
                company_id=company.id,
                site_id=site.id,
                role="QA Manager",
                is_active=True,
            )
            db.add(mem)
            logger.info("Added ChemCorp membership for Priyanshu")
        else:
            mem.is_active = True
            mem.site_id = site.id
            mem.role = "QA Manager"
        await db.flush()

        # 4. Supplier: ChemCorp
        stmt_sup = select(Supplier).where(Supplier.company_id == company.id, Supplier.name == "ChemCorp")
        res_sup = await db.execute(stmt_sup)
        supplier = res_sup.scalar_one_or_none()
        if not supplier:
            supplier = Supplier(
                company_id=company.id,
                name="ChemCorp",
                code="SUP-CHEM-01",
                status="Approved",
                risk_level="Medium",
            )
            db.add(supplier)
            await db.flush()
            logger.info("Created Supplier: ChemCorp (%s)", supplier.id)

        # 5. Batch: API-2026-041
        stmt_b041 = select(Batch).where(Batch.company_id == company.id, Batch.batch_number == "API-2026-041")
        res_b041 = await db.execute(stmt_b041)
        b041 = res_b041.scalar_one_or_none()
        if not b041:
            b041 = Batch(
                company_id=company.id,
                site_id=site.id,
                batch_number="API-2026-041",
                product_name="Paracetamol API",
                product_code="PARA-API-01",
                recipe_version="v4.2",
                site_plant="Bengaluru",
                status="In Progress",
                release_status="Pending",
                started_at=datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc),
            )
            db.add(b041)
            await db.flush()
            logger.info("Created Batch: API-2026-041 (%s)", b041.id)

        # 6. Raw Material: Acetic Anhydride
        stmt_rm = select(RawMaterial).where(RawMaterial.batch_id == b041.id, RawMaterial.lot_number == "RM-2026-001")
        res_rm = await db.execute(stmt_rm)
        rm = res_rm.scalar_one_or_none()
        if not rm:
            rm = RawMaterial(
                company_id=company.id,
                supplier_id=supplier.id,
                batch_id=b041.id,
                name="Acetic Anhydride",
                material_code="RM-AA-04",
                lot_number="RM-2026-001",
                status="Approved",
            )
            db.add(rm)
            await db.flush()
            logger.info("Created Raw Material: Acetic Anhydride (RM-2026-001)")

        # 7. Manufacturing Steps for API-2026-041:
        # Step 1 - Charge, Step 2 - Preparation, Step 3 - Reaction (Warning)
        stmt_steps = select(ManufacturingStep).where(ManufacturingStep.batch_id == b041.id)
        res_steps = await db.execute(stmt_steps)
        existing_steps = list(res_steps.scalars().all())
        step3 = None
        if not existing_steps:
            s1 = ManufacturingStep(
                batch_id=b041.id, company_id=company.id, step_number=1, name="Step 1 - Charge", status="completed"
            )
            s2 = ManufacturingStep(
                batch_id=b041.id, company_id=company.id, step_number=2, name="Step 2 - Preparation", status="completed"
            )
            s3 = ManufacturingStep(
                batch_id=b041.id,
                company_id=company.id,
                step_number=3,
                name="Step 3 - Reaction",
                status="warning",
                warning_details="Temperature excursion detected: 84 °C exceeds limit 76–80 °C.",
            )
            db.add_all([s1, s2, s3])
            await db.flush()
            step3 = s3
            logger.info("Created Manufacturing Steps for API-2026-041")
        else:
            for s in existing_steps:
                if s.step_number == 3:
                    step3 = s
                    break

        # 8. In-Process Checks for API-2026-041:
        # Temperature (76–80 °C, Actual: 84 °C, OUT OF SPEC)
        # Pressure (1.0–1.5 bar, Actual: 1.2 bar, In Spec)
        # pH (6.5–7.5, Actual: 7.1, In Spec)
        # Reaction Time (2–3 hr, Actual: 2.5 hr, In Spec)
        stmt_ipcs = select(InProcessCheck).where(InProcessCheck.batch_id == b041.id)
        res_ipcs = await db.execute(stmt_ipcs)
        existing_ipcs = list(res_ipcs.scalars().all())
        temp_ipc = None
        if not existing_ipcs:
            temp_ipc = InProcessCheck(
                batch_id=b041.id,
                step_id=step3.id if step3 else None,
                company_id=company.id,
                parameter="Temperature",
                specification="76–80 °C",
                actual_value="84 °C",
                status="OUT OF SPEC",
                checked_at=datetime(2026, 9, 27, 10, 15, tzinfo=timezone.utc),
                checked_by="Operator Ramesh",
                notes="Temperature spike occurred during exothermic addition phase. Peak 84 °C sustained for 18 min.",
            )
            p_ipc = InProcessCheck(
                batch_id=b041.id,
                step_id=step3.id if step3 else None,
                company_id=company.id,
                parameter="Pressure",
                specification="1.0–1.5 bar",
                actual_value="1.2 bar",
                status="In Spec",
                checked_at=datetime(2026, 9, 27, 10, 20, tzinfo=timezone.utc),
                checked_by="Operator Ramesh",
            )
            ph_ipc = InProcessCheck(
                batch_id=b041.id,
                step_id=step3.id if step3 else None,
                company_id=company.id,
                parameter="pH",
                specification="6.5–7.5",
                actual_value="7.1",
                status="In Spec",
                checked_at=datetime(2026, 9, 27, 10, 25, tzinfo=timezone.utc),
                checked_by="QC Analyst Priya",
            )
            rt_ipc = InProcessCheck(
                batch_id=b041.id,
                step_id=step3.id if step3 else None,
                company_id=company.id,
                parameter="Reaction Time",
                specification="2–3 hr",
                actual_value="2.5 hr",
                status="In Spec",
                checked_at=datetime(2026, 9, 27, 10, 30, tzinfo=timezone.utc),
                checked_by="Operator Ramesh",
            )
            db.add_all([temp_ipc, p_ipc, ph_ipc, rt_ipc])
            await db.flush()
            logger.info("Created In-Process Checks for API-2026-041")
        else:
            for ipc in existing_ipcs:
                if ipc.parameter == "Temperature":
                    temp_ipc = ipc
                    break

        # 9. Deviation: DEV-2026-018
        stmt_dev = select(Deviation).where(Deviation.reference == "DEV-2026-018")
        res_dev = await db.execute(stmt_dev)
        dev018 = res_dev.scalar_one_or_none()
        if not dev018:
            dev018 = Deviation(
                reference="DEV-2026-018",
                source=DeviationSource.TEXT,
                reported_by="QA Lead Priyanshu",
                occurred_on=date(2026, 9, 27),
                detected_on=date(2026, 9, 27),
                company_id=company.id,
                site_id=site.id,
                site_plant="Bengaluru",
                department="Manufacturing",
                responsible_team="API Production Team 2",
                product_name="Paracetamol API",
                product_code="PARA-API-01",
                batch_number="API-2026-041",
                manufacturing_stage="Step 3 - Reaction",
                equipment="Reactor R-101",
                title="Reactor temperature exceeded limit",
                description=(
                    "During Paracetamol API manufacturing Batch API-2026-041 at Step 3 (Reaction), "
                    "the approved temperature range was 76–80 °C. The actual temperature reached 84 °C "
                    "for approximately 18 minutes. Automatic cooling response was delayed. Production was "
                    "halted and QA was notified immediately."
                ),
                deviation_type=DeviationType.PROCESS,
                expected_condition="76–80 °C",
                actual_condition="84 °C",
                duration="18 min",
                parameter="Temperature",
                immediate_action="Exothermic charge halted, emergency chilled-water bypass engaged, reaction cooled to 77 °C. Batch held.",
                batch_status=BatchStatus.ON_HOLD,
                qa_notified=True,
                impact=Impact.PRODUCT_QUALITY,
                severity=Severity.MAJOR,
                assessment_reason="Temperature excursion above 80 °C creates potential risk of degradation and impurity formation for Paracetamol API.",
                status=DeviationStatus.UNDER_REVIEW,
                workflow_status="investigation",
                batch_id=b041.id,
                manufacturing_step_id=step3.id if step3 else None,
                in_process_check_id=temp_ipc.id if temp_ipc else None,
                ai_recommended_impact="product_quality",
                ai_recommended_severity="major",
                ai_reason="Excursion above upper specification limit (80 °C) in critical chemical reaction stage directly influences API impurity profiles.",
                ai_evidence=[
                    {
                        "document_name": "SOP-014 v3.2: Chemical Synthesis & Reactor Temperature Control",
                        "section": "Section 3.2 - Reaction Parameter Limits for Paracetamol API",
                        "snippet": "Approved temperature range is 76–80 °C for Step 3 (Reaction) of Paracetamol API synthesis. Any excursion above 80 °C increases risk of degradation and 4-aminophenol impurities.",
                    }
                ],
            )
            db.add(dev018)
            await db.flush()
            logger.info("Created Deviation: DEV-2026-018 (%s)", dev018.id)
            if temp_ipc:
                temp_ipc.deviation_id = dev018.id
                await db.flush()
        else:
            dev018.company_id = company.id
            dev018.batch_id = b041.id
            dev018.workflow_status = "investigation"
            if temp_ipc:
                dev018.in_process_check_id = temp_ipc.id
            await db.flush()

        # 10. Investigation: INV-2026-012
        stmt_inv = select(Investigation).where(Investigation.reference == "INV-2026-012")
        res_inv = await db.execute(stmt_inv)
        inv012 = res_inv.scalar_one_or_none()
        if not inv012:
            inv012 = Investigation(
                reference="INV-2026-012",
                deviation_id=dev018.id,
                company_id=company.id,
                title="Investigation into Reactor R-101 Temperature Excursion (84 °C)",
                status="in_progress",
                lead_investigator="QA Lead Priyanshu",
                overview="Formal investigation to determine cause of cooling delay during Step 3 of Batch API-2026-041.",
                investigation_plan="Review BMR, DCS continuous temperature logs, maintenance work order history for valve actuator, and conduct 5 Whys RCA.",
                methodology="Root Cause Analysis & 5 Whys",
            )
            db.add(inv012)
            await db.flush()

            # Tasks
            tasks_data = [
                (1, "Review batch manufacturing record", "QA", "Completed", "2026-09-28", datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc), "Verified charging rate was compliant with recipe v4.2."),
                (2, "Review equipment history", "Engineering", "Completed", "2026-09-29", datetime(2026, 9, 29, 11, 30, tzinfo=timezone.utc), "Cooling-valve actuator EQ-ACT-04 exhibited mechanical lag during full stroke."),
                (3, "Interview operator", "QA", "Pending", "2026-10-02", None, "Interview shift operator regarding audible DCS alarm timing."),
                (4, "Assess product impact", "QA", "Pending", "2026-10-03", None, "Review HPLC assay and 4-aminophenol impurity testing."),
            ]
            for num, title, owner, st, due, comp_at, notes in tasks_data:
                t = InvestigationTask(
                    investigation_id=inv012.id,
                    company_id=company.id,
                    task_number=num,
                    title=title,
                    owner=owner,
                    status=st,
                    due_date=due,
                    completed_at=comp_at,
                    notes=notes,
                )
                db.add(t)

            # Evidence
            evs = [
                ("Temperature log", "log", "Reactor R-101 DCS Temp Recording", "Peak temperature 84 °C recorded at Step 3 Reaction; excursion duration 18 min."),
                ("Maintenance record", "maintenance", "EQ-ACT-04 Service Sheet", "Cooling valve actuator last inspected 14 months ago; PM frequency was quarterly visual only."),
                ("SOP-014 v3.2", "sop", "SOP-014 v3.2 Section 3.2", "Approved temperature range 76–80 °C. Cooling response required within 3 min."),
            ]
            for title, ev_type, ref_doc, snippet in evs:
                ev = InvestigationEvidence(
                    investigation_id=inv012.id,
                    company_id=company.id,
                    title=title,
                    evidence_type=ev_type,
                    reference_doc=ref_doc,
                    snippet=snippet,
                    attached_by="QA Lead Priyanshu",
                )
                db.add(ev)
            await db.flush()
            logger.info("Created Investigation: INV-2026-012 with tasks and evidence")

        # 11. Root Cause Analysis: RCA-2026-012
        stmt_rca = select(RootCauseAnalysis).where(RootCauseAnalysis.reference == "RCA-2026-012")
        res_rca = await db.execute(stmt_rca)
        rca012 = res_rca.scalar_one_or_none()
        if not rca012:
            rca012 = RootCauseAnalysis(
                reference="RCA-2026-012",
                investigation_id=inv012.id,
                deviation_id=dev018.id,
                company_id=company.id,
                problem_statement="Temperature reached 84 °C during Step 3 (Reaction).",
                why_1="Cooling response was delayed.",
                why_2="Cooling valve did not respond correctly.",
                why_3="Valve actuator malfunctioned.",
                why_4="Maintenance did not detect actuator degradation.",
                why_5="Preventive maintenance controls did not adequately cover actuator degradation.",
                root_cause_summary="Inadequate preventive-maintenance control for the cooling-valve actuator.",
                category="Equipment / Maintenance",
                contributing_factors="Actuator seal wear leading to delayed pneumatic stroke response; PM schedule lacked periodic stroke-time verification.",
                is_confirmed=True,
                confirmed_by="QA Lead Priyanshu",
                confirmed_at=datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc),
            )
            db.add(rca012)
            await db.flush()
            logger.info("Created Root Cause: RCA-2026-012 (Confirmed)")

        # 12. CAPA: CAPA-2026-009
        stmt_capa = select(Capa).where(Capa.reference == "CAPA-2026-009")
        res_capa = await db.execute(stmt_capa)
        capa009 = res_capa.scalar_one_or_none()
        if not capa009:
            capa009 = Capa(
                reference="CAPA-2026-009",
                deviation_id=dev018.id,
                investigation_id=inv012.id,
                root_cause_id=rca012.id,
                company_id=company.id,
                title="Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators",
                root_cause_summary="Inadequate preventive-maintenance control for the cooling-valve actuator.",
                status="completed",
                created_by="Engineering Lead Rajesh",
                target_completion_date=date(2026, 10, 15),
            )
            db.add(capa009)
            await db.flush()

            # Corrective Action
            ca1 = CapaAction(
                capa_id=capa009.id,
                company_id=company.id,
                action_type="CORRECTIVE",
                action_description="Overhaul Reactor 2 cooling valve actuator and replace degraded pneumatic seals",
                owner="Engineering",
                due_date="02 Oct 2026",
                status="Completed",
                evidence_reference="Maintenance record EQ-ACT-04 / Replacement Tag",
                completed_at=datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc),
            )
            # Preventive Action
            ca2 = CapaAction(
                capa_id=capa009.id,
                company_id=company.id,
                action_type="PREVENTIVE",
                action_description="Revise SOP-014 to enforce mandatory 60-day pneumatic valve preventive maintenance PM-204",
                owner="Engineering",
                due_date="05 Oct 2026",
                status="Completed",
                evidence_reference="Draft SOP-014 v3.3 & revised PM checklist PM-204",
                completed_at=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
            )
            db.add_all([ca1, ca2])
            await db.flush()
            logger.info("Created CAPA: CAPA-2026-009 with Corrective & Preventive actions (Completed)")
        else:
            capa009.title = "Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators"
            capa009.status = "completed"
            stmt_acts = select(CapaAction).where(CapaAction.capa_id == capa009.id)
            res_acts = await db.execute(stmt_acts)
            for a in res_acts.scalars().all():
                if a.action_type == "CORRECTIVE":
                    a.action_description = "Overhaul Reactor 2 cooling valve actuator and replace degraded pneumatic seals"
                    a.status = "Completed"
                    if not a.completed_at:
                        a.completed_at = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)
                elif a.action_type == "PREVENTIVE":
                    a.action_description = "Revise SOP-014 to enforce mandatory 60-day pneumatic valve preventive maintenance PM-204"
                    a.status = "Completed"
                    if not a.completed_at:
                        a.completed_at = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
            await db.flush()

        # 13. Effectiveness Check: EFF-2026-009
        stmt_eff = select(EffectivenessCheck).where(EffectivenessCheck.reference == "EFF-2026-009")
        res_eff = await db.execute(stmt_eff)
        eff009 = res_eff.scalar_one_or_none()
        if not eff009:
            eff009 = EffectivenessCheck(
                reference="EFF-2026-009",
                capa_id=capa009.id,
                deviation_id=dev018.id,
                company_id=company.id,
                plan_description="Monitor the next five batches with no recurrence",
                criteria="Zero temperature excursions during reaction phase across next 5 consecutive batches (API-2026-042 to 046)",
                monitored_batches=[
                    {"batch_number": "API-2026-042", "parameter": "Temperature", "specification": "76–80 °C", "actual": "78.2 °C", "outcome": "No recurrence", "status": "Passed"},
                    {"batch_number": "API-2026-043", "parameter": "Temperature", "specification": "76–80 °C", "actual": "77.5 °C", "outcome": "No recurrence", "status": "Passed"},
                    {"batch_number": "API-2026-044", "parameter": "Temperature", "specification": "76–80 °C", "actual": "79.0 °C", "outcome": "No recurrence", "status": "Passed"},
                    {"batch_number": "API-2026-045", "parameter": "Temperature", "specification": "76–80 °C", "actual": "78.0 °C", "outcome": "No recurrence", "status": "Passed"},
                    {"batch_number": "API-2026-046", "parameter": "Temperature", "specification": "76–80 °C", "actual": "77.8 °C", "outcome": "No recurrence", "status": "Passed"},
                ],
                ai_summary="No recurrence of the temperature excursion was observed across the monitored batches.",
                status="effective",
                reviewed_by="QA Director Dr. Sarah Jenkins",
                reviewed_at=datetime(2026, 9, 30, 11, 0, tzinfo=timezone.utc),
                comments="All five consecutive batches (API-2026-042 through API-2026-046) operated within 76–80 °C with zero thermal excursions. Actuator overhaul and SOP-014 revision demonstrated recurrence elimination.",
            )
            db.add(eff009)
            await db.flush()
            logger.info("Created Effectiveness Check: EFF-2026-009 (Effective, 5/5 compliant)")
        else:
            eff009.status = "effective"
            eff009.reviewed_by = "QA Director Dr. Sarah Jenkins"
            eff009.reviewed_at = datetime(2026, 9, 30, 11, 0, tzinfo=timezone.utc)
            eff009.comments = "All five consecutive batches (API-2026-042 through API-2026-046) operated within 76–80 °C with zero thermal excursions. Actuator overhaul and SOP-014 revision demonstrated recurrence elimination."
            await db.flush()

        # 14. Monitored Batches in Batches table: API-2026-042 to 046
        monitored_batch_ids = ["API-2026-042", "API-2026-043", "API-2026-044", "API-2026-045", "API-2026-046"]
        for b_num in monitored_batch_ids:
            stmt_mb = select(Batch).where(Batch.company_id == company.id, Batch.batch_number == b_num)
            res_mb = await db.execute(stmt_mb)
            if not res_mb.scalar_one_or_none():
                mb = Batch(
                    company_id=company.id,
                    site_id=site.id,
                    batch_number=b_num,
                    product_name="Paracetamol API",
                    product_code="PARA-API-01",
                    recipe_version="v4.2",
                    site_plant="Bengaluru",
                    status="Completed",
                    release_status="Released",
                    started_at=datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc),
                    completed_at=datetime(2026, 9, 28, 18, 0, tzinfo=timezone.utc),
                )
                db.add(mb)
        await db.flush()

        # 15. Batch Release Review: BR-2026-041
        stmt_br = select(BatchRelease).where(BatchRelease.reference == "BR-2026-041")
        res_br = await db.execute(stmt_br)
        br041 = res_br.scalar_one_or_none()
        if not br041:
            br041 = BatchRelease(
                reference="BR-2026-041",
                batch_id=b041.id,
                company_id=company.id,
                status="PENDING",
                decision_rationale="Pending completion of post-CAPA quality review and QA disposition.",
                checklist_review={
                    "manufacturing_record": True,
                    "in_process_checks": True,
                    "deviation_investigated": True,
                    "root_cause_confirmed": True,
                    "capa_completed": True,
                    "effectiveness_reviewed": True,
                    "qc_results": True,
                },
            )
            db.add(br041)
            await db.flush()
            logger.info("Created Batch Release: BR-2026-041 (Pending QA disposition)")

        # Additional Batch Release to have 2 pending in dashboard
        stmt_b047 = select(Batch).where(Batch.company_id == company.id, Batch.batch_number == "API-2026-047")
        res_b047 = await db.execute(stmt_b047)
        b047 = res_b047.scalar_one_or_none()
        if not b047:
            b047 = Batch(
                company_id=company.id,
                site_id=site.id,
                batch_number="API-2026-047",
                product_name="Paracetamol API",
                product_code="PARA-API-01",
                recipe_version="v4.2",
                site_plant="Bengaluru",
                status="In Progress",
                release_status="Pending",
            )
            db.add(b047)
            await db.flush()
            br047 = BatchRelease(
                reference="BR-2026-047",
                batch_id=b047.id,
                company_id=company.id,
                status="PENDING",
                decision_rationale="Routine release review in progress.",
            )
            db.add(br047)
            await db.flush()

        # 16. Complaint: COM-2026-003
        stmt_com = select(Complaint).where(Complaint.reference == "COM-2026-003")
        res_com = await db.execute(stmt_com)
        com003 = res_com.scalar_one_or_none()
        if not com003:
            com003 = Complaint(
                reference="COM-2026-003",
                company_id=company.id,
                batch_id=b041.id,
                deviation_id=dev018.id,
                product_name="Paracetamol API",
                description="Customer query regarding batch synthesis consistency and thermal profile during reaction stage.",
                potential_impact="Review Required",
                recall_assessment="Pending",
                status="open",
            )
            db.add(com003)
            await db.flush()
            logger.info("Created Complaint: COM-2026-003")

        # 17. Seed additional deviations so dashboard metrics reflect 12 deviations, 4 investigations, 3 CAPAs
        additional_devs = [
            ("DEV-2026-019", "Purified Water Conductivity Excursion", "utility", Severity.MINOR, DeviationStatus.UNDER_REVIEW, "investigation"),
            ("DEV-2026-020", "Cleanroom Differential Pressure Drop in Filling Suite", "environmental", Severity.MAJOR, DeviationStatus.UNDER_REVIEW, "investigation"),
            ("DEV-2026-021", "Weight Variation in Granulation Blend", "process", Severity.MINOR, DeviationStatus.SUBMITTED, "reported"),
            ("DEV-2026-022", "Autoclave Sterilization Temperature Hold Drop", "equipment", Severity.CRITICAL, DeviationStatus.UNDER_REVIEW, "investigation"),
            ("DEV-2026-023", "Raw Material Certificate of Analysis Discrepancy", "material", Severity.MINOR, DeviationStatus.SUBMITTED, "reported"),
            ("DEV-2026-024", "Packaging Label Line Clearance Observation", "documentation", Severity.MINOR, DeviationStatus.CLOSED, "closed"),
            ("DEV-2026-025", "Vial Depyrogenation Tunnel Belt Speed Fluctuation", "equipment", Severity.MAJOR, DeviationStatus.CLOSED, "closed"),
            ("DEV-2026-026", "Laboratory HPLC Baseline Drift on Impurity Assay", "laboratory", Severity.MINOR, DeviationStatus.SUBMITTED, "reported"),
            ("DEV-2026-027", "HVAC HEPA Filter Differential Pressure Action Level", "utility", Severity.MAJOR, DeviationStatus.SUBMITTED, "reported"),
            ("DEV-2026-028", "Nitrogen Purge Pressure Low in Reaction Vessel", "process", Severity.MINOR, DeviationStatus.SUBMITTED, "reported"),
            ("DEV-2026-029", "Operator Gowning Breach in Grade B Air Shower", "personnel", Severity.MINOR, DeviationStatus.CLOSED, "closed"),
        ]
        for ref, title, dtype, sev, st, wflow in additional_devs:
            stmt_chk = select(Deviation).where(Deviation.reference == ref)
            if not (await db.execute(stmt_chk)).scalar_one_or_none():
                d = Deviation(
                    reference=ref,
                    title=title,
                    description=f"Automated quality event intake for {title.lower()}.",
                    deviation_type=DeviationType(dtype),
                    severity=sev,
                    status=st,
                    workflow_status=wflow,
                    company_id=company.id,
                    site_id=site.id,
                    site_plant="Bengaluru",
                    occurred_on=date(2026, 9, 25),
                )
                db.add(d)
        await db.flush()

        # Seed additional investigations to reach 4 investigations
        extra_invs = [
            ("INV-2026-013", "DEV-2026-019", "Investigation for DEV-2026-019", "Purified Water loop bioburden & conductivity investigation"),
            ("INV-2026-014", "DEV-2026-020", "Investigation for DEV-2026-020", "Cleanroom differential pressure drop & damper review"),
            ("INV-2026-015", "DEV-2026-022", "Investigation for DEV-2026-022", "Autoclave AC-02 heating element and RTD sensor calibration"),
        ]
        for ref, dev_ref, title, desc in extra_invs:
            stmt_ci = select(Investigation).where(Investigation.reference == ref)
            if not (await db.execute(stmt_ci)).scalar_one_or_none():
                res_d = await db.execute(select(Deviation).where(Deviation.reference == dev_ref))
                dev_target = res_d.scalar_one_or_none()
                if dev_target:
                    inv_x = Investigation(
                        reference=ref,
                        deviation_id=dev_target.id,
                        company_id=company.id,
                        title=title,
                        status="in_progress",
                        lead_investigator="QA Investigator",
                        overview=desc,
                    )
                    db.add(inv_x)
        await db.flush()

        # Seed additional CAPAs to reach 3 CAPAs
        extra_capas = [
            ("CAPA-2026-010", "DEV-2026-020", "HEPA filter seal replacement and automated pressure monitoring", "in_progress"),
            ("CAPA-2026-011", "DEV-2026-022", "Autoclave RTD temperature probe recalibration & dual-sensor redundancy", "in_progress"),
        ]
        for ref, dev_ref, title, st in extra_capas:
            stmt_cc = select(Capa).where(Capa.reference == ref)
            if not (await db.execute(stmt_cc)).scalar_one_or_none():
                res_d = await db.execute(select(Deviation).where(Deviation.reference == dev_ref))
                dev_target = res_d.scalar_one_or_none()
                c_x = Capa(
                    reference=ref,
                    deviation_id=dev_target.id if dev_target else dev018.id,
                    company_id=company.id,
                    title=title,
                    root_cause_summary="Sensor drift and mechanical wear under continuous operational duty cycle.",
                    status=st,
                    created_by="Engineering Lead",
                    target_completion_date=date(2026, 10, 20),
                )
                db.add(c_x)
        await db.commit()
        logger.info("Successfully seeded Connected QMS reference demo scenario and records!")

    await dispose_engine()


def main():
    asyncio.run(seed_qms())


if __name__ == "__main__":
    main()
