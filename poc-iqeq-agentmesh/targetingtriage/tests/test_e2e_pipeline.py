import httpx
import pytest

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_e2e_pipeline_full_run():
    """
    Triggers the full 6-agent pipeline and verifies integrity of the JSON response.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/score_accounts")
        assert response.status_code == 200
        
        data = response.json()
        assert "pipeline_run_id" in data
        assert "accounts" in data
        assert len(data["accounts"]) == 50

@pytest.mark.asyncio
async def test_golden_path_acme_90001():
    """
    Verifies that ACME-EU-90001 (High ML, High Context) results in Bucket A and No Conflict.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/score_accounts")
        data = response.json()
        
        # Find 90001
        acc = next((a for a in data["accounts"] if a["account_id"] == "ACME-EU-90001"), None)
        assert acc is not None
        assert acc["priority_bucket"] == "A"
        assert acc["conflict_flag"] == False
        assert acc["ml_score"] >= 0.70

@pytest.mark.asyncio
async def test_conflict_detection_acme_90003():
    """
    Verifies that ACME-EU-90003 (Low ML, High Context) results in a Conflict Flag.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/score_accounts")
        data = response.json()
        
        # Find 90003
        acc = next((a for a in data["accounts"] if a["account_id"] == "ACME-EU-90003"), None)
        assert acc is not None
        assert acc["conflict_flag"] == True
        assert acc["ml_score"] <= 0.30
        assert acc["priority_bucket"] == "A" # Overridden by LLM context

@pytest.mark.asyncio
async def test_conflict_detection_acme_90002():
    """
    Verifies that ACME-EU-90002 (High ML, Low Context) results in a Conflict Flag.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/score_accounts")
        data = response.json()
        
        # Find 90002
        acc = next((a for a in data["accounts"] if a["account_id"] == "ACME-EU-90002"), None)
        assert acc is not None
        assert acc["conflict_flag"] == True
        assert acc["ml_score"] >= 0.70
        assert acc["priority_bucket"] == "C" # Overridden by LLM context
