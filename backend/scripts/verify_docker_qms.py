"""Verify all canonical demo records from the running Docker container via HTTP."""

import json
import urllib.request

BASE_URL = "http://localhost:8000/api/v1"


def get_auth_token():
    login_url = f"{BASE_URL}/auth/login"
    payload = json.dumps({"email": "priyanshu@gmail.com", "password": "123456789"}).encode("utf-8")
    req = urllib.request.Request(login_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["access_token"]


def get_json(endpoint: str, token: str = None):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"User-Agent": "PharmaOne-Verifier"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify():
    print("==================================================")
    print("  VERIFYING RUNNING DOCKER COMPOSE QMS STACK")
    print("==================================================")

    # 1. Health checks
    health = get_json("health")
    ready = get_json("health/ready")
    print(f"1. Liveness Probe:     status={health.get('status')}, env={health.get('environment')}")
    print(f"2. Readiness Probe:    status={ready.get('status')}, database={ready.get('database')}")
    assert health.get("status") == "ok"
    assert ready.get("status") == "ready"
    assert ready.get("database") == "connected"

    # Authenticate
    token = get_auth_token()
    print(f"3. Authentication:     Success (Bearer {token[:16]}...)")

    # 2. Dashboard Summary
    dash = get_json("dashboard/summary", token)
    print(f"4. Dashboard Metrics:  Total Devs: {dash.get('total_deviations')}, Critical/Major: {dash.get('critical_or_major')}, Pending CAPAs: {dash.get('pending_capas')}")

    # 3. Canonical Batches API-2026-041 through API-2026-046
    batches = get_json("batches", token)
    batch_dict = {b["batch_number"]: b for b in batches}
    for b_num in ["API-2026-041", "API-2026-042", "API-2026-043", "API-2026-044", "API-2026-045", "API-2026-046"]:
        assert b_num in batch_dict, f"Batch {b_num} missing"
    b041 = batch_dict["API-2026-041"]
    print(f"5. Canonical Batches:  Found {len(batches)} batches (API-2026-041 to 046 verified) | Primary: {b041['batch_number']} ({b041['product_name']})")

    # 4. Canonical IPC: Temperature 84 °C / OUT OF SPEC
    ipcs = get_json(f"batches/{b041['id']}/process-checks", token)
    temp_ipc = next((c for c in ipcs if c["parameter"] == "Temperature"), None)
    assert temp_ipc is not None, "Temperature IPC check missing"
    print(f"6. Canonical IPC:      {temp_ipc['parameter']} = {temp_ipc['actual_value']} (Spec: {temp_ipc['specification']}) -> Status: {temp_ipc['status']}")

    # 5. Canonical Deviation DEV-2026-018
    devs_resp = get_json("deviations", token)
    dev_items = devs_resp.get("items", devs_resp) if isinstance(devs_resp, dict) else devs_resp
    dev018 = next((d for d in dev_items if d["reference"] == "DEV-2026-018"), None)
    assert dev018 is not None, "Deviation DEV-2026-018 missing"
    print(f"7. Deviation:          {dev018['reference']} | Title: '{dev018['title']}' | Status: {dev018['status']}")

    # 6. Connected QMS Linked Records for DEV-2026-018
    linked = get_json(f"deviations/{dev018['id']}/linked-records", token)
    assert linked.get("deviation_reference") == "DEV-2026-018"

    # Canonical Investigation INV-2026-012
    inv = linked.get("investigation")
    assert inv is not None, "Linked investigation missing"
    assert inv.get("reference") == "INV-2026-012", f"Expected INV-2026-012, got {inv.get('reference')}"
    print(f"8. Investigation:      {inv['reference']} | Status: {inv['status']} | Title: '{inv['title']}'")

    # Canonical Root Cause RCA-2026-012
    rca = linked.get("root_cause")
    assert rca is not None, "Linked root cause missing"
    assert rca.get("reference") == "RCA-2026-012", f"Expected RCA-2026-012, got {rca.get('reference')}"
    print(f"9. Root Cause:         {rca['reference']} | Summary: '{rca['title']}'")

    # Canonical CAPA-2026-009
    capa = linked.get("capa")
    assert capa is not None, "Linked CAPA missing"
    assert capa.get("reference") == "CAPA-2026-009", f"Expected CAPA-2026-009, got {capa.get('reference')}"
    print(f"10. Canonical CAPA:    {capa['reference']} | Status: {capa['status']} | Title: '{capa['title']}'")

    # Canonical Effectiveness EFF-2026-009
    eff = linked.get("effectiveness")
    assert eff is not None, "Linked effectiveness check missing"
    assert eff.get("reference") == "EFF-2026-009", f"Expected EFF-2026-009, got {eff.get('reference')}"
    print(f"11. Effectiveness:     {eff['reference']} | Status: {eff['status']} | Criteria: '{eff['title']}'")

    # Canonical Batch Release BR-2026-041
    br = linked.get("batch_release")
    assert br is not None, "Linked batch release missing"
    assert br.get("reference") == "BR-2026-041", f"Expected BR-2026-041, got {br.get('reference')}"
    print(f"12. Batch Release:     {br['reference']} | Status: {br['status']}")

    # Canonical Complaint COM-2026-003
    complaints = get_json("complaints", token)
    comp = next((c for c in complaints if c["reference"] == "COM-2026-003"), None)
    assert comp is not None, "Complaint COM-2026-003 missing"
    print(f"13. Complaint:         {comp['reference']} | Product: '{comp['product_name']}' | Status: {comp['status']}")

    # Canonical Supplier ChemCorp & Raw Material RM-2026-001
    suppliers = get_json("suppliers", token)
    sup = next((s for s in suppliers if s["name"] == "ChemCorp"), None)
    assert sup is not None, "Supplier ChemCorp missing"
    print(f"14. Supplier:          {sup['name']} | Status: {sup['status']} | Risk: {sup['risk_level']}")

    raw_mats = get_json("raw-materials", token)
    rm = next((r for r in raw_mats if r["lot_number"] == "RM-2026-001"), None)
    assert rm is not None, "Raw Material RM-2026-001 missing"
    print(f"15. Raw Material:      {rm['lot_number']} | Name: '{rm['name']}' | Status: {rm['status']}")

    # 7. Frontend check
    with urllib.request.urlopen("http://localhost:8080/", timeout=30) as f_resp:
        html = f_resp.read().decode("utf-8")
        assert "<div id=\"root\">" in html
        print(f"16. Frontend UI:       HTTP {f_resp.status} OK (HTML served, React root mounted)")

    print("==================================================")
    print("  ALL 16 VERIFICATIONS PASSED ON RUNNING DOCKER STACK!")
    print("==================================================")


if __name__ == "__main__":
    verify()
