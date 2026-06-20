import pytest
from pydantic import ValidationError
from app.schemas import AccountResult, PipelineResponse, NBAAction

def test_nba_action_valid():
    action = NBAAction(action_type="call", description="Test Call", due_in_days=5)
    assert action.action_type == "call"

def test_account_result_valid():
    res = AccountResult(
        account_id="ACME-01",
        priority_bucket="A",
        ml_score=0.85,
        confidence_level=0.9,
        conflict_flag=False,
        rationale_text="Test description",
        nba_actions=[NBAAction(action_type="call", description="Call now", due_in_days=1)]
    )
    assert res.priority_bucket == "A"

def test_account_result_invalid_bucket():
    with pytest.raises(ValidationError):
        # Bucket must be A, B, or C
        AccountResult(
            account_id="ACME-01",
            priority_bucket="D", 
            ml_score=0.85,
            confidence_level=0.9,
            conflict_flag=False,
            rationale_text="Test",
            nba_actions=[]
        )

def test_account_result_invalid_score_high():
    with pytest.raises(ValidationError):
        # Score must be <= 1
        AccountResult(
            account_id="ACME-01",
            priority_bucket="A",
            ml_score=1.5,
            confidence_level=0.9,
            conflict_flag=False,
            rationale_text="Test",
            nba_actions=[]
        )

def test_account_result_invalid_score_low():
    with pytest.raises(ValidationError):
        # Score must be >= 0
        AccountResult(
            account_id="ACME-01",
            priority_bucket="A",
            ml_score=-0.1,
            confidence_level=0.9,
            conflict_flag=False,
            rationale_text="Test",
            nba_actions=[]
        )

def test_pipeline_response_minimal():
    resp = PipelineResponse(
        pipeline_run_id="uuid-123",
        generated_at="2026-04-08T12:00:00Z",
        model_version="v1",
        accounts=[]
    )
    assert resp.pipeline_run_id == "uuid-123"
    assert len(resp.accounts) == 0
