"""Golden-path account ranks in top whitespace tier (mock LLM)."""

import pytest

from app.modules.whitespace.clustering import run_clustering
from app.modules.whitespace.data_agent import run_whitespace_data_agent
from app.modules.whitespace.scoring import run_whitespace_scoring


@pytest.fixture
def mock_campaign_chain(monkeypatch):
    async def _fake(prompt_text: str, inputs: dict) -> dict:
        return {
            "messaging_angle": "Test hook",
            "campaign_brief_text": "Test brief",
            "primary_cta": "Book a call",
        }

    monkeypatch.setattr(
        "app.modules.whitespace.campaign_brief_agent.run_poc3_campaign_chain",
        _fake,
    )


@pytest.mark.asyncio
async def test_golden_path_top_accounts_and_clusters(mock_campaign_chain):
    from app.modules.whitespace.whitespace_orchestrator import run_whitespace_pipeline

    out = await run_whitespace_pipeline(console=False)
    top_ids = [a["account_id"] for a in out["top_accounts"][:5]]
    assert "ACME-EU-90001" in top_ids

    brief_clusters = {b["cluster_id"] for b in out["campaign_briefs"]}
    gold_cluster = next(
        a["cluster_id"]
        for a in out["top_accounts"]
        if a["account_id"] == "ACME-EU-90001"
    )
    assert gold_cluster in brief_clusters

    region_warnings = [
        f
        for f in out["validation_flags"]
        if f["flag_type"] == "warning" and "region_fit" in f["anomaly_note"]
    ]
    assert len(region_warnings) >= 1


def test_scoring_pipeline_loads_runtime_data():
    raw = run_whitespace_data_agent(trace_id="test")
    scored = run_whitespace_scoring(raw)
    clustered = run_clustering(scored)
    ac = clustered["by_account"].get("ACME-EU-90001")
    assert ac is not None
    assert ac["total_ws_potential_eur"] > 0
