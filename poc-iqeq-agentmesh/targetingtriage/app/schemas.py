from pydantic import BaseModel, Field
from typing import List, Optional, Any, TypedDict
from uuid import UUID
from datetime import datetime

class AgentMeshState(TypedDict):
    """
    State definition for the LangGraph Agentic Mesh.
    """
    trace_id: str
    poc_id: int # 1: Targeting, 2: Planning, 3: Whitespace
    raw_data: Optional[dict]
    scoring_results: List[dict]
    reasoning_results: List[dict]
    planning_results: List[dict] # Result of POC 2
    validation_results: List[dict]
    final_output: Optional[dict]
    errors: List[str]
    telemetry: dict

# NBA Action Schema
class NBAAction(BaseModel):
    action_type: str
    description: str
    reasoning: str
    due_in_days: int

# Single Account Result Schema
class AccountResult(BaseModel):
    account_id: str
    account_name: str
    contact_person: str
    priority_bucket: str = Field(..., pattern="^[A-C]$")
    ml_score: float = Field(..., ge=0, le=1)
    confidence_level: float = Field(..., ge=0, le=1)
    conflict_flag: bool
    rationale_text: str
    nba_actions: List[NBAAction]
    # POC 2 specific (Optional)
    brief_text: Optional[str] = None
    call_plan_text: Optional[str] = None
    api_score: Optional[float] = None
    whitespace_summary: Optional[List[dict]] = None

# Final Pipeline Response Schema
class PipelineResponse(BaseModel):
    pipeline_run_id: str
    generated_at: str
    model_version: str
    accounts: List[AccountResult]

# --- Internal Agent Communication Schemas ---

# Scoring Agent Output (Per Account)
class ScoringOutput(BaseModel):
    account_id: str
    propensity_score: float
    confidence_level: float

# Reasoning Agent Output (Per Account)
class ReasoningOutput(BaseModel):
    account_id: str
    priority_bucket: str
    rationale_text: str
    suggested_nba: NBAAction

# Validation Agent Output (Per Account)
class ValidationOutput(BaseModel):
    account_id: str
    conflict_flag: bool

# --- POC 2: Account Planning Schemas ---

class PlanningOutput(BaseModel):
    account_id: str
    brief_text: str
    call_plan_text: str
    api_score: float
    total_ws_potential_eur: float
    whitespace_summary: List[dict]
