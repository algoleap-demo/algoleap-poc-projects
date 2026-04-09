import os

from fastapi.testclient import TestClient


def _import_api():
    # Import lazily so tests can fail with a clear message if SQLite isn't ready.
    from data.scripts import scoring_api  # type: ignore

    return scoring_api


def test_health_ok():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["loaded_accounts"] >= 150


def test_score_accounts_default_sorted_and_limited():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    resp = client.post("/score_accounts", json={})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 50
    prop = [r["buy_upsell_propensity"] for r in rows]
    assert prop == sorted(prop, reverse=True)


def test_score_accounts_filters():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    req = {
        "countries": ["LU", "NL"],
        "segments": ["FAM"],
        "status_filter": "prospect",
        "min_propensity": 0.2,
        "limit": 25,
    }
    resp = client.post("/score_accounts", json=req)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) <= 25
    for r in rows:
        assert r["country"] in {"LU", "NL"}
        assert r["segment"] == "FAM"
        assert r["status"] == "prospect"
        assert r["buy_upsell_propensity"] >= 0.2


def test_score_accounts_invalid_status_filter():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)
    resp = client.post("/score_accounts", json={"status_filter": "invalid"})
    assert resp.status_code == 422


def test_account_view_happy_path_and_404():
    scoring_api = _import_api()
    client = TestClient(scoring_api.app)

    # Use an account_id from the loaded dataframe
    first_id = scoring_api.merged_df.iloc[0]["account_id"]

    resp = client.get(f"/account_view/{first_id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["account_id"] == first_id
    assert "features" in payload
    assert isinstance(payload["features"], dict)
    assert "service_penetration_score" in payload["features"]

    resp_404 = client.get("/account_view/ACC_XX_9999")
    assert resp_404.status_code == 404

