"""Verify complete lifecycle workflow via HTTP against running Docker stack connected to Supabase."""

import json
import urllib.request
import uuid

BASE_URL = "http://localhost:8000/api/v1"


def req(path: str, method: str = "GET", data: dict = None, token: str = None):
    url = f"{BASE_URL}/{path}"
    headers = {"User-Agent": "LifecycleVerifier"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as resp:
        content = resp.read().decode("utf-8")
        return json.loads(content) if content else {}


def test_lifecycle():
    print("=" * 65)
    print("TESTING FULL QMS LIFECYCLE WORKFLOW ON DOCKER + SUPABASE")
    print("=" * 65)

    # 1. Login
    print("\n[Step 1] Logging in...")
    login = req("auth/login", method="POST", data={"email": "priyanshu@gmail.com", "password": "123456789"})
    token = login["access_token"]
    user = login["user"]
    print(f"  -> Logged in as: {user['full_name']} ({user['role']}) at {user['company_name']}")

    # 2. Get Batches
    print("\n[Step 2] Fetching batches from Supabase...")
    batches = req("batches", token=token)
    assert len(batches) > 0, "No batches found"
    b041 = next(b for b in batches if b["batch_number"] == "API-2026-041")
    print(f"  -> Selected Batch: {b041['batch_number']} (ID: {b041['id']})")

    # 3. Create Deviation
    unique_suffix = uuid.uuid4().hex[:6].upper()
    dev_ref = f"DEV-DOCKER-{unique_suffix}"
    print(f"\n[Step 3] Creating new Deviation: {dev_ref}...")
    dev_data = {
        "title": f"Docker Validation Excursion {unique_suffix}",
        "description": "Temperature fluctuation observed during reactor agitation cycle for Docker integration testing.",
        "occurred_on": "2026-09-30",
        "detected_on": "2026-09-30",
        "batch_number": b041["batch_number"],
        "product_name": b041["product_name"],
        "deviation_type": "process",
        "expected_condition": "76-80 °C",
        "actual_condition": "82.5 °C",
        "severity": "minor",
        "impact": "product_quality",
        "status": "under_review",
        "batch_id": b041["id"]
    }
    new_dev = req("deviations", method="POST", data=dev_data, token=token)
    dev_id = new_dev["id"]
    print(f"  -> Deviation Created: {new_dev['reference']} (ID: {dev_id})")

    # 4. Start Investigation
    print("\n[Step 4] Starting Investigation for Deviation...")
    inv = req(f"deviations/{dev_id}/start-investigation", method="POST", token=token)
    inv_id = inv["id"]
    print(f"  -> Investigation Started: {inv['reference']} (Status: {inv['status']})")

    # 5. Add Investigation Task & Evidence
    print("\n[Step 5] Adding Investigation Task & Evidence...")
    task = req(f"investigations/{inv_id}/tasks", method="POST", data={
        "title": "Check thermocouple calibration certificate",
        "owner": "Instrumentation Lead",
        "due_date": "2026-10-05",
        "status": "Pending"
    }, token=token)
    print(f"  -> Task Added: #{task['task_number']} '{task['title']}'")

    task_up = req(f"investigations/{inv_id}/tasks/{task['id']}", method="PATCH", data={
        "status": "Completed",
        "notes": "Calibration certificate verified valid until December 2026."
    }, token=token)
    print(f"  -> Task Updated: Status={task_up['status']}")

    ev = req(f"investigations/{inv_id}/evidence", method="POST", data={
        "title": "Thermocouple TC-101 Calibration Record",
        "evidence_type": "certificate",
        "snippet": "TC-101 verified at 80.0 °C reference point. Drift: +0.1 °C.",
        "reference_doc": "CAL-2026-881"
    }, token=token)
    print(f"  -> Evidence Attached: '{ev['title']}'")

    # 6. Confirm 5 Whys Root Cause Analysis
    print("\n[Step 6] Confirming 5 Whys Root Cause Analysis...")
    rca = req(f"investigations/{inv_id}/root-cause", method="POST", data={
        "problem_statement": "Reactor temperature reached 82.5 °C briefly during agitation start",
        "why_1": "Agitator speed caused local exothermic surge",
        "why_2": "VFD ramp rate parameter was set too steep",
        "why_3": "Recipe v4.2 acceleration curve was not optimized for slurry viscosity",
        "why_4": "Rheology study update was not cross-referenced in engineering recipe",
        "why_5": "Agitator ramp-rate specification omitted from SOP review cycle",
        "root_cause_summary": "Agitator ramp-rate profile requires revision in SOP-014",
        "contributing_factors": ["High initial slurry solids content"],
        "category": "Procedure / Recipe",
        "human_confirmed": True
    }, token=token)
    print(f"  -> RCA Confirmed: {rca['reference']} - '{rca['root_cause_summary']}'")

    # 7. Complete Investigation
    print("\n[Step 7] Completing Investigation...")
    comp_inv = req(f"investigations/{inv_id}/complete", method="POST", data={
        "conclusion": "Agitator ramp-rate profile caused transient thermal rise; product unaffected.",
        "product_impact_assessment": "Batch quality within specifications.",
        "completed_by": "Priyanshu (QA Manager)"
    }, token=token)
    print(f"  -> Investigation Completed: Status={comp_inv['status']}")

    # 8. Create CAPA
    print("\n[Step 8] Creating CAPA...")
    capa = req("capas", method="POST", data={
        "deviation_id": dev_id,
        "investigation_id": inv_id,
        "title": f"Revise Agitator Ramp Rates for Slurry Batching ({unique_suffix})",
        "root_cause_summary": rca["root_cause_summary"],
        "created_by": "Priyanshu"
    }, token=token)
    capa_id = capa["id"]
    print(f"  -> CAPA Created: {capa['reference']} - '{capa['title']}'")

    # Add Action to CAPA
    action = req(f"capas/{capa_id}/actions", method="POST", data={
        "action_type": "CORRECTIVE",
        "action_description": "Update VFD acceleration curve in PLC recipe v4.3",
        "owner": "Automation Team",
        "due_date": "2026-10-15",
        "status": "Completed"
    }, token=token)
    print(f"  -> CAPA Action Added: '{action['action_description']}' (Status={action['status']})")

    # 9. Record Effectiveness
    print("\n[Step 9] Recording Effectiveness Check...")
    eff = req(f"capas/{capa_id}/effectiveness", method="POST", data={
        "status": "effective",
        "comments": "Agitation ramp rate validated on subsequent batches with no temperature spikes.",
        "reviewed_by": "Priyanshu"
    }, token=token)
    print(f"  -> Effectiveness Recorded: {eff['reference']} - Status={eff['status']}")

    # 10. Close Deviation
    print("\n[Step 10] Formally Closing Deviation...")
    closed_dev = req(f"deviations/{dev_id}/close", method="POST", data={
        "closure_reason": "All investigation tasks completed, RCA confirmed, CAPA verified effective.",
        "closure_summary": "Thermal excursion fully resolved with zero quality impact.",
        "closed_by": "Priyanshu (QA Manager)"
    }, token=token)
    print(f"  -> Deviation Formally Closed: Status={closed_dev['status']}, Workflow={closed_dev['workflow_status']}")

    # 11. Verify Data Persistence via Linked Records Tree from Supabase
    print("\n[Step 11] Verifying Connected Tree from Supabase...")
    linked = req(f"deviations/{dev_id}/linked-records", token=token)
    assert linked["investigation"]["reference"] == inv["reference"]
    assert linked["root_cause"]["reference"] == rca["reference"]
    assert linked["capa"]["reference"] == capa["reference"]
    assert linked["effectiveness"]["reference"] == eff["reference"]
    print(f"  -> Deviation:     {linked['deviation_reference']}")
    print(f"  -> Investigation: {linked['investigation']['reference']} ({linked['investigation']['status']})")
    print(f"  -> Root Cause:    {linked['root_cause']['reference']} ({linked['root_cause']['title']})")
    print(f"  -> CAPA:          {linked['capa']['reference']} ({linked['capa']['status']})")
    print(f"  -> Effectiveness: {linked['effectiveness']['reference']} ({linked['effectiveness']['status']})")

    print("\n" + "=" * 65)
    print(">>> COMPLETE QMS LIFECYCLE WORKFLOW VERIFIED SUCCESSFULLY! <<<")
    print("=" * 65)


if __name__ == "__main__":
    test_lifecycle()
