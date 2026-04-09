"""Phase 5 — Audit override endpoint tests (offline, no Gemini needed)."""

from fastapi.testclient import TestClient


def _import_api():
    from data.scripts import scoring_api  # type: ignore

    return scoring_api


def _valid_account_id(scoring_api):
    return scoring_api.merged_df.iloc[0]["account_id"]


# ── POST /overrides ──────────────────────────────────────────────────────────

def test_create_override_valid():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    acc_id = _valid_account_id(scoring_api)

    resp = client.post("/overrides", json={
        "account_id": acc_id,
        "field_changed": "priority_bucket",
        "old_value": "B",
        "new_value": "A",
        "failure_category": "Hallucination",
        "user": "test@iqeq.com",
        "notes": "Model hallucinated a reason",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["account_id"] == acc_id
    assert data["failure_category"] == "Hallucination"
    assert data["field_changed"] == "priority_bucket"
    assert data["id"] > 0


def test_create_override_invalid_category():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    acc_id = _valid_account_id(scoring_api)

    resp = client.post("/overrides", json={
        "account_id": acc_id,
        "field_changed": "priority_bucket",
        "old_value": "A",
        "new_value": "C",
        "failure_category": "Wrong Category",
    })
    assert resp.status_code == 422


def test_create_override_invalid_field():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    acc_id = _valid_account_id(scoring_api)

    resp = client.post("/overrides", json={
        "account_id": acc_id,
        "field_changed": "score",
        "old_value": "0.5",
        "new_value": "0.9",
        "failure_category": "Data Latency",
    })
    assert resp.status_code == 422


def test_create_override_unknown_account():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)

    resp = client.post("/overrides", json={
        "account_id": "ACC_XX_9999",
        "field_changed": "priority_bucket",
        "old_value": "B",
        "new_value": "A",
        "failure_category": "Policy Misalignment",
    })
    assert resp.status_code == 404


# ── GET /overrides ───────────────────────────────────────────────────────────

def test_list_overrides():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)

    resp = client.get("/overrides")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Should have at least the one we created in earlier tests
    if data:
        assert "account_id" in data[0]
        assert "failure_category" in data[0]


def test_list_overrides_filter_by_category():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)

    resp = client.get("/overrides", params={"failure_category": "Hallucination"})
    assert resp.status_code == 200
    for item in resp.json():
        assert item["failure_category"] == "Hallucination"


# ── GET /overrides/summary ───────────────────────────────────────────────────

def test_overrides_summary():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)

    resp = client.get("/overrides/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "by_category" in data
    assert "by_field" in data
    assert "total" in data
    assert isinstance(data["total"], int)
