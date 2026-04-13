from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

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

# --- POC 2: Account Planning Models ---

class CallObjective(BaseModel):
    objective: str
    rationale: str

class CallAgendaItem(BaseModel):
    step: int
    topic: str
    key_question: str

class PlanningResult(BaseModel):
    account_id: str
    account_name: str
    contact_person: str
    brief_markdown: str
    objectives: List[CallObjective]
    agenda: List[CallAgendaItem]
    conflict_flag: bool = False

class PlanningPipelineResponse(BaseModel):
    pipeline_run_id: str
    generated_at: str
    model_version: str
    results: List[PlanningResult]

class Contact(BaseModel):
    contact_id: str
    full_name: str
    role: str
    seniority: str
    engagement_score: float
    influence_score: float

class WhitespaceCell(BaseModel):
    product_id: str
    product_line: str
    has_product: bool
    potential_revenue_bucket: str
    expected_rev_eur: float
    ws_score: float

class AccountPlanningPack(AccountResult):
    api_score: float
    total_ws_potential_eur: float
    relationship_depth: float
    brief_text: str
    call_plan_text: str
    whitespace_summary: List[WhitespaceCell]
    review_notes: str


# --- POC2 §08 API response (strict) ---
class WhitespaceSummaryItem(BaseModel):
    product: str
    expected_rev_eur: float


class PlanningNBAActionV2(BaseModel):
    action_type: str
    description: str
    due_in_days: int
    reasoning: str = ""


class POC2AccountOutput(BaseModel):
    account_id: str
    api_score: float = Field(..., ge=0, le=1)
    propensity_score: float = Field(..., ge=0, le=1)
    confidence_level: float = Field(..., ge=0, le=1)
    total_ws_potential_eur: float
    relationship_depth: float = Field(..., ge=0, le=1)
    brief_text: str
    call_plan_text: str
    whitespace_summary: List[WhitespaceSummaryItem]
    nba_actions: List[PlanningNBAActionV2]
    conflict_flag: bool
    review_notes: str


class POC2PipelineResponse(BaseModel):
    pipeline_run_id: str
    generated_at: str
    model_version: str
    accounts: List[POC2AccountOutput]

# --- LangGraph State Definitions ---

from typing import TypedDict, Any

class AgentMeshState(TypedDict):
    trace_id: str
    raw_data: Optional[dict]
    scoring_results: List[dict]
    reasoning_results: List[dict]
    validation_results: List[dict]
    final_output: Optional[dict]
    errors: List[str]
    telemetry: dict

class PlanningState(TypedDict):
    trace_id: str
    account_id: str
    raw_data: Optional[dict]
    scoring_results: List[dict]
    brief_results: Optional[dict]
    validation_results: List[dict]
    final_output: Optional[dict]
    errors: List[str]
    telemetry: dict
