from fastapi.testclient import TestClient


def _import_api():
    from data.scripts import scoring_api  # type: ignore

    return scoring_api


def test_prioritize_accounts_valid(monkeypatch):
    scoring_api = _import_api()

    client = TestClient(scoring_api.app)
    scored = client.post("/score_accounts", json={"limit": 3}).json()
    ids = [r["account_id"] for r in scored]

    def fake_generate_text(**kwargs):
        return (
            "["
            f'{{\"account_id\":\"{ids[0]}\",\"priority_bucket\":\"A\",\"rationale_text\":\"High propensity and whitespace.\"}},'
            f'{{\"account_id\":\"{ids[1]}\",\"priority_bucket\":\"B\",\"rationale_text\":\"Good fit, moderate propensity.\"}},'
            f'{{\"account_id\":\"{ids[2]}\",\"priority_bucket\":\"C\",\"rationale_text\":\"Lower urgency vs peers.\"}}'
            "]"
        )

    monkeypatch.setattr(scoring_api, "generate_text", fake_generate_text)

    resp = client.post("/prioritize_accounts", json={"limit": 3})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["llm_provider"] == "gemini"
    assert len(payload["results"]) == 3
    assert {r["priority_bucket"] for r in payload["results"]} <= {"A", "B", "C"}


def test_prioritize_accounts_rejects_unknown_account(monkeypatch):
    scoring_api = _import_api()

    def fake_generate_text(**kwargs):
        return '[{"account_id":"ACC_XX_9999","priority_bucket":"A","rationale_text":"Test"}]'

    monkeypatch.setattr(scoring_api, "generate_text", fake_generate_text)

    client = TestClient(scoring_api.app)
    resp = client.post("/prioritize_accounts", json={"limit": 5})
    assert resp.status_code == 502


def test_prioritize_accounts_rejects_invalid_bucket(monkeypatch):
    scoring_api = _import_api()
    valid_id = scoring_api.merged_df.iloc[0]["account_id"]

    def fake_generate_text(**kwargs):
        return f'[{{"account_id":"{valid_id}","priority_bucket":"D","rationale_text":"Test"}}]'

    monkeypatch.setattr(scoring_api, "generate_text", fake_generate_text)

    client = TestClient(scoring_api.app)
    resp = client.post("/prioritize_accounts", json={"limit": 1})
    assert resp.status_code == 502

