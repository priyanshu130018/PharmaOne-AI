import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

SAMPLE_CONTEXT = {
    "title_short_description": "Sterility test failure observed in Autoclave AC-02",
    "detailed_description": "Chamber temperature dropped to 118.5°C during the 20-minute sterilization hold phase.",
    "deviation_type": "equipment",
    "related_product_material": "SterileInjectable 100mL",
    "batch_lot_number": "LOT-2026-042",
    "equipment": "Autoclave AC-02",
    "parameter": "Chamber temperature",
    "approved_range": "121.1°C +/- 0.5°C",
    "actual_value": "118.5°C",
    "duration": "20 minutes",
    "immediate_action": "Cycle aborted, entire autoclave load placed on hold under tag Q-882 pending QA review",
    "qa_notified": True,
    "missing_information": ["department", "site_plant"],
}

SAMPLE_ASSESSMENT = {
    "recommended_severity": "critical",
    "recommended_impact": "product_quality",
    "reason": "Chamber temperature dropped below approved sterilization threshold, threatening sterility assurance.",
}


async def test_chat_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as unauthed:
        resp = await unauthed.post("/api/v1/deviations/chat", json={"message": "What is the severity?"})
        assert resp.status_code == 401


async def test_chat_answers_batch_and_equipment(client: AsyncClient):
    # Batch
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Which batch was affected?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "LOT-2026-042" in resp.json()["response"]

    # Equipment
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What equipment was involved?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "Autoclave AC-02" in resp.json()["response"]


async def test_chat_answers_temperature_and_range(client: AsyncClient):
    # Actual value
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What was the actual temperature?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "118.5" in resp.json()["response"]

    # Approved range
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What was the approved range?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "121.1" in resp.json()["response"]

    # Within approved range
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Was the actual value within the approved range?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    res_text = resp.json()["response"].lower()
    assert "no" in res_text or "outside" in res_text


async def test_chat_answers_duration_action_qa(client: AsyncClient):
    # Duration
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "How long was the excursion?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "20 minutes" in resp.json()["response"]

    # Immediate action
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What immediate action was taken?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "aborted" in resp.json()["response"].lower() or "hold" in resp.json()["response"].lower()

    # QA notified
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Was QA notified?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "yes" in resp.json()["response"].lower()


async def test_chat_answers_severity_and_form_override(client: AsyncClient):
    # Why is this critical?
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Why is this critical?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "critical" in resp.json()["response"].lower()

    # Form override distinction: user changes severity to Major on the form
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What is the severity on the form?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
            "current_form": {"severity": "major"},
        },
    )
    assert resp.status_code == 200
    text = resp.json()["response"].lower()
    assert "major" in text
    assert "critical" in text  # Distinguishes form vs initial recommendation


async def test_chat_answers_missing_info_and_unknown(client: AsyncClient):
    # Missing information
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What information is missing?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "department" in resp.json()["response"] or "site_plant" in resp.json()["response"]

    # Unknown query / not in text
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Who was the supplier of the rubber stoppers in 2021?",
            "context": SAMPLE_CONTEXT,
            "assessment": SAMPLE_ASSESSMENT,
        },
    )
    assert resp.status_code == 200
    assert "not contain enough information" in resp.json()["response"]


async def test_chat_handles_unavailable_severity(client: AsyncClient):
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What is the AI severity assessment?",
            "context": SAMPLE_CONTEXT,
            "assessment": {"severity": None, "recommended_severity": None},
        },
    )
    assert resp.status_code == 200
    assert "severity assessment is currently unavailable" in resp.json()["response"]


async def test_chat_natural_language_form_updates(client: AsyncClient):
    # 1. Update site
    resp1 = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Set the site to Demo Manufacturing Site.",
            "current_form": {"site_plant": "Plant 1"},
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["intent"] == "update_form"
    assert isinstance(data1["changes"], list)
    assert len(data1["changes"]) == 1
    site_change = data1["changes"][0]
    assert site_change["field"] in ("site", "site_plant")
    assert site_change["label"] == "Site / Plant"
    assert site_change["old_value"] == "Plant 1"
    assert site_change["new_value"] == "Demo Manufacturing Site"
    assert "Change applied." in data1["message"]

    # 2. Update batch and title
    resp2 = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Change the batch to LOT-2026-051 and change the title to Granulation impeller speed exceeded the approved range.",
            "current_form": {"batch_number": "LOT-2026-042", "title": "Old title"},
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["intent"] == "update_form"
    assert len(data2["changes"]) == 2
    batch_ch = next(c for c in data2["changes"] if c["field"] in ("batch", "batch_number"))
    title_ch = next(c for c in data2["changes"] if c["field"] == "title")
    assert batch_ch["label"] == "Batch / Lot Number"
    assert batch_ch["old_value"] == "LOT-2026-042"
    assert batch_ch["new_value"] == "LOT-2026-051"
    assert title_ch["label"] == "Title / Short Description"
    assert title_ch["new_value"] == "Granulation impeller speed exceeded the approved range"
    assert "2 changes applied." in data2["message"]

    # 3. Update date of occurrence
    resp3 = await client.post(
        "/api/v1/deviations/chat",
        json={"message": "The incident happened on 27 September 2026 at 10:35 AM."},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["intent"] == "update_form"
    date_ch = data3["changes"][0]
    assert date_ch["field"] == "occurred_on"
    assert date_ch["label"] == "Date of Occurrence"
    assert date_ch["new_value"] == "2026-09-27"
    assert "Change applied." in data3["message"]

    # 4. Update description
    resp4 = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Actually, change the description to mention that the batch was placed on QA hold and was not released."
        },
    )
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["intent"] == "update_form"
    desc_ch = data4["changes"][0]
    assert desc_ch["field"] == "description"
    assert desc_ch["label"] == "Detailed Description"
    assert "QA hold" in desc_ch["new_value"]


async def test_chat_multi_field_update_example(client: AsyncClient):
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "Set the site to Demo Manufacturing Site, product to Paracetamol Tablets 500 mg, and batch to LOT-2026-051.",
            "current_form": {"site_plant": "Plant 1", "batch_number": "LOT-2026-042"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "update_form"
    assert len(data["changes"]) == 3
    assert data["message"] == "3 changes applied."

    fields = {c["field"]: c for c in data["changes"]}
    assert "site" in fields or "site_plant" in fields
    assert "product_name" in fields or "product" in fields
    assert "batch_number" in fields or "batch" in fields

    site_c = fields.get("site") or fields.get("site_plant")
    assert site_c["label"] == "Site / Plant"
    assert site_c["old_value"] == "Plant 1"
    assert site_c["new_value"] == "Demo Manufacturing Site"

    prod_c = fields.get("product_name") or fields.get("product")
    assert prod_c["label"] == "Related Product / Material"
    assert prod_c["new_value"] == "Paracetamol Tablets 500 mg"

    batch_c = fields.get("batch_number") or fields.get("batch")
    assert batch_c["label"] == "Batch / Lot Number"
    assert batch_c["old_value"] == "LOT-2026-042"
    assert batch_c["new_value"] == "LOT-2026-051"


async def test_chat_clarification_on_ambiguous_change(client: AsyncClient):
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={"message": "Change it"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "answer_question"
    assert data["changes"] == []
    assert "I couldn't determine which form field you want to change" in data["message"]


async def test_chat_question_returns_current_batch_no_changes(client: AsyncClient):
    resp = await client.post(
        "/api/v1/deviations/chat",
        json={
            "message": "What is the current batch number?",
            "current_form": {"batch_number": "LOT-2026-051"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "answer_question"
    assert data["changes"] == []
    assert "LOT-2026-051" in data["message"]
    assert "Change applied" not in data["message"]

