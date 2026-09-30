import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import Company
from app.models.qms import Batch, ManufacturingStep, InProcessCheck, RawMaterial, Supplier, Complaint


@pytest.mark.asyncio
async def test_batch_and_process_checks(client: AsyncClient):
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        res = await db.execute(select(Company))
        company = res.scalars().first()
        assert company is not None

        batch = Batch(
            id=uuid.uuid4(),
            company_id=company.id,
            batch_number="API-2026-041",
            product_name="Paracetamol API",
            recipe_version="v4.2",
            site_plant="Bengaluru",
            status="In Progress",
            release_status="Pending",
        )
        db.add(batch)
        await db.flush()

        step3 = ManufacturingStep(
            id=uuid.uuid4(),
            batch_id=batch.id,
            company_id=company.id,
            step_number=3,
            name="Step 3 - Reaction",
            status="warning",
            warning_details="Reactor temperature reached 84 °C (Limit 76–80 °C)",
        )
        db.add(step3)
        await db.flush()

        ipc_temp = InProcessCheck(
            id=uuid.uuid4(),
            batch_id=batch.id,
            step_id=step3.id,
            company_id=company.id,
            parameter="Temperature",
            specification="76–80 °C",
            actual_value="84 °C",
            status="OUT OF SPEC",
        )
        db.add(ipc_temp)
        await db.commit()

        batch_id = str(batch.id)

    # 1. Query batches list
    resp = await client.get("/api/v1/batches")
    assert resp.status_code == 200, resp.text
    batches = resp.json()
    assert isinstance(batches, list)
    assert any(b["batch_number"] == "API-2026-041" for b in batches)

    # 2. Fetch batch by ID
    resp = await client.get(f"/api/v1/batches/{batch_id}")
    assert resp.status_code == 200
    b_data = resp.json()
    assert b_data["batch_number"] == "API-2026-041"
    assert b_data["product_name"] == "Paracetamol API"
    assert len(b_data["manufacturing_steps"]) >= 1

    # 3. Fetch batch process checks
    resp_ipc = await client.get(f"/api/v1/batches/{batch_id}/process-checks")
    assert resp_ipc.status_code == 200
    checks = resp_ipc.json()
    temp_check = next((c for c in checks if c["parameter"] == "Temperature"), None)
    assert temp_check is not None
    assert temp_check["status"] == "OUT OF SPEC"
    assert temp_check["actual_value"] == "84 °C"


@pytest.mark.asyncio
async def test_connected_quality_event_lifecycle(client: AsyncClient):
    """
    Validates the complete primary connected quality lifecycle:
    Batch & IPC -> Deviation -> Investigation -> 5 Whys Root Cause -> CAPA -> Effectiveness -> Closure -> Batch Release
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        res = await db.execute(select(Company))
        company = res.scalars().first()

        batch = Batch(
            id=uuid.uuid4(),
            company_id=company.id,
            batch_number="API-2026-041",
            product_name="Paracetamol API",
            recipe_version="v4.2",
            site_plant="Bengaluru",
            status="In Progress",
            release_status="Pending",
        )
        db.add(batch)
        await db.flush()

        step3 = ManufacturingStep(
            id=uuid.uuid4(),
            batch_id=batch.id,
            company_id=company.id,
            step_number=3,
            name="Step 3 - Reaction",
            status="warning",
            warning_details="Reactor temperature reached 84 °C",
        )
        db.add(step3)
        await db.flush()

        ipc_temp = InProcessCheck(
            id=uuid.uuid4(),
            batch_id=batch.id,
            step_id=step3.id,
            company_id=company.id,
            parameter="Temperature",
            specification="76–80 °C",
            actual_value="84 °C",
            status="OUT OF SPEC",
        )
        db.add(ipc_temp)
        await db.commit()

        batch_id = str(batch.id)
        step_id = str(step3.id)
        ipc_id = str(ipc_temp.id)

    # 1. Create Deviation from IPC parameter
    dev_payload = {
        "title": "Reactor temperature exceeded limit",
        "description": "Reactor 2 temperature reached 84 °C during Step 3 Reaction (limit 76–80 °C). Excursion persisted for 18 min.",
        "deviation_type": "environmental",
        "severity": "major",
        "impact": "product_quality",
        "batch_number": "API-2026-041",
        "batch_id": batch_id,
        "manufacturing_step_id": step_id,
        "in_process_check_id": ipc_id,
        "source": "manual",
        "site_plant": "Bengaluru",
        "department": "Production",
        "reported_by": "priyanshu@gmail.com",
    }
    resp = await client.post("/api/v1/deviations", json=dev_payload)
    assert resp.status_code == 201, resp.text
    dev_data = resp.json()
    deviation_id = dev_data["id"]
    assert dev_data["reference"].startswith("DEV-")

    # 2. Start Investigation
    resp_inv = await client.post(f"/api/v1/deviations/{deviation_id}/start-investigation")
    assert resp_inv.status_code == 200, resp_inv.text
    inv_data = resp_inv.json()
    investigation_id = inv_data["id"]
    assert inv_data["reference"].startswith("INV-")

    # 3. Add Investigation Task & Complete
    resp_task = await client.post(
        f"/api/v1/investigations/{investigation_id}/tasks",
        json={
            "title": "Review batch manufacturing record and temperature log",
            "owner": "QA",
            "due_date": "2026-03-27",
            "status": "Completed"
        }
    )
    assert resp_task.status_code in (200, 201)

    # Add evidence
    resp_ev = await client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={
            "title": "SCADA Temperature Log",
            "evidence_type": "Log",
            "summary": "Confirms temperature peak at 84 °C for 18 minutes duration",
            "source": "SCADA"
        }
    )
    assert resp_ev.status_code in (200, 201)

    # Complete Investigation
    resp_comp = await client.post(
        f"/api/v1/investigations/{investigation_id}/complete",
        json={
            "conclusion": "Excursion driven by cooling valve actuator degradation; product degradation thresholds not breached.",
            "completed_by": "QA Manager"
        }
    )
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"].lower() == "completed"

    # 4. Perform 5 Whys Root Cause Analysis
    rca_payload = {
        "problem_statement": "Temperature reached 84 °C.",
        "why_1": "Cooling response was delayed.",
        "why_2": "Cooling valve did not respond correctly.",
        "why_3": "Valve actuator malfunctioned.",
        "why_4": "Maintenance did not detect actuator degradation.",
        "why_5": "Preventive maintenance controls did not adequately cover actuator degradation.",
        "root_cause_summary": "Inadequate preventive-maintenance control for the cooling-valve actuator.",
        "contributing_factors": "High duty cycle, Actuator positioner calibration drift",
        "confirmed_by": "QA Manager"
    }
    resp_rca = await client.post(
        f"/api/v1/investigations/{investigation_id}/root-cause",
        json=rca_payload
    )
    assert resp_rca.status_code == 200, resp_rca.text
    rca_data = resp_rca.json()
    assert rca_data["root_cause_summary"] == rca_payload["root_cause_summary"]

    # 5. Create CAPA
    capa_payload = {
        "deviation_id": deviation_id,
        "investigation_id": investigation_id,
        "root_cause_id": rca_data["id"],
        "title": "Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators",
        "root_cause_summary": rca_data["root_cause_summary"]
    }
    resp_capa = await client.post("/api/v1/capas", json=capa_payload)
    assert resp_capa.status_code in (200, 201), resp_capa.text
    capa_data = resp_capa.json()
    capa_id = capa_data["id"]

    # Add Corrective & Preventive Actions
    resp_act1 = await client.post(
        f"/api/v1/capas/{capa_id}/actions",
        json={
            "action_type": "CORRECTIVE",
            "action_description": "Replace malfunctioning cooling-valve actuator on Reactor 2",
            "owner": "Engineering",
            "due_date": "2026-03-25",
            "status": "Completed"
        }
    )
    assert resp_act1.status_code in (200, 201)

    resp_act2 = await client.post(
        f"/api/v1/capas/{capa_id}/actions",
        json={
            "action_type": "PREVENTIVE",
            "action_description": "Update SOP-014 PM checklist to inspect actuator response every 30 days",
            "owner": "Maintenance",
            "due_date": "2026-03-30",
            "status": "Completed"
        }
    )
    assert resp_act2.status_code in (200, 201)

    # 6. Record 5-Batch Effectiveness Review
    eff_payload = {
        "status": "effective",
        "comments": "5/5 consecutive commercial batches compliant with zero excursions.",
        "reviewed_by": "QA Director"
    }
    resp_eff = await client.post(f"/api/v1/capas/{capa_id}/effectiveness", json=eff_payload)
    assert resp_eff.status_code == 200, resp_eff.text
    assert resp_eff.json()["status"] == "effective"

    # 7. Check Linked Records Graph
    resp_linked = await client.get(f"/api/v1/deviations/{deviation_id}/linked-records")
    assert resp_linked.status_code == 200
    links = resp_linked.json()
    assert links["batch"] is not None
    assert links["investigation"] is not None
    assert links["root_cause"] is not None
    assert links["capa"] is not None
    assert links["effectiveness"] is not None

    # 8. Close Deviation
    close_payload = {
        "closure_reason": "All CAPA actions executed and verified effective across 5 commercial batches.",
        "closure_summary": "Comprehensive investigation INV-2026-012 completed. Root cause remediated and verified effective."
    }
    resp_close = await client.post(f"/api/v1/deviations/{deviation_id}/close", json=close_payload)
    assert resp_close.status_code == 200, resp_close.text
    closed_dev = resp_close.json()
    assert closed_dev["workflow_status"].lower() == "closed"
    assert closed_dev["closed_by"] is not None

    # 9. Verify Closed Deviation Cannot Be Modified (Enforce Compliance Lock)
    resp_edit = await client.put(
        f"/api/v1/deviations/{deviation_id}",
        json={"title": "Unauthorized change attempt after closure"}
    )
    assert resp_edit.status_code in (400, 422)
    assert "Cannot modify closed deviation" in resp_edit.text


@pytest.mark.asyncio
async def test_qms_closure_quality_gates(client: AsyncClient):
    """
    Validates that premature deviation closure is strictly blocked if quality gates are incomplete.
    """
    # Create fresh deviation
    resp = await client.post(
        "/api/v1/deviations",
        json={
            "title": "Incomplete deviation for gate testing",
            "description": "Testing closure prevention when investigation is not completed.",
            "deviation_type": "equipment",
            "severity": "minor",
            "impact": "product_quality",
            "source": "manual",
            "site_plant": "Bengaluru",
        }
    )
    assert resp.status_code == 201
    dev_id = resp.json()["id"]

    # Attempt closure without investigation -> must return 400
    resp_close = await client.post(
        f"/api/v1/deviations/{dev_id}/close",
        json={"closure_reason": "Premature attempt", "closure_summary": "Attempting to bypass gates"}
    )
    assert resp_close.status_code in (400, 422)
    assert "Cannot close deviation" in resp_close.text


@pytest.mark.asyncio
async def test_ai_quality_assistant_endpoints(client: AsyncClient):
    """
    Verifies that AI Quality Assistant endpoints produce grounded advisory proposals.
    """
    # Suggest investigation plan
    resp_inv_ai = await client.post(
        "/api/v1/ai/investigation/suggest",
        json={
            "title": "Reactor temperature excursion on Batch API-2026-041",
            "parameter": "Temperature",
            "actual_value": "84 °C",
            "expected_condition": "76–80 °C",
            "equipment": "Reactor 2"
        }
    )
    assert resp_inv_ai.status_code == 200
    data_inv = resp_inv_ai.json()
    assert "suggested_tasks" in data_inv
    assert "evidence_to_review" in data_inv

    # Generate 5 Whys
    resp_5w = await client.post(
        "/api/v1/ai/root-cause/generate",
        json={
            "problem_statement": "Temperature reached 84 °C.",
            "deviation_context": "Reactor 2 temperature excursion above 76–80 °C"
        }
    )
    assert resp_5w.status_code == 200
    data_5w = resp_5w.json()
    assert "why_1" in data_5w
    assert "final_root_cause" in data_5w

    # Suggest CAPA actions
    resp_capa_ai = await client.post(
        "/api/v1/ai/capa/suggest",
        json={
            "root_cause": "Inadequate preventive-maintenance control for cooling-valve actuator",
            "deviation_context": "Reactor 2 temperature exceeded 80 °C limit"
        }
    )
    assert resp_capa_ai.status_code == 200
    data_capa = resp_capa_ai.json()
    assert "corrective_actions" in data_capa
    assert "preventive_actions" in data_capa

    # Summarize effectiveness
    resp_eff_ai = await client.post(
        "/api/v1/ai/effectiveness/summarize",
        json={
            "monitored_batches": [
                {"batchNumber": "API-2026-042", "status": "In Spec"},
                {"batchNumber": "API-2026-043", "status": "In Spec"},
            ],
            "capa_reference": "CAPA-2026-009"
        }
    )
    assert resp_eff_ai.status_code == 200
    data_eff = resp_eff_ai.json()
    assert "summary" in data_eff

    # Draft closure summary
    resp_close_ai = await client.post(
        "/api/v1/ai/closure/draft",
        json={
            "deviation_reference": "DEV-2026-018",
            "title": "Reactor temperature exceeded limit"
        }
    )
    assert resp_close_ai.status_code == 200
    data_close = resp_close_ai.json()
    assert "draft_summary" in data_close
