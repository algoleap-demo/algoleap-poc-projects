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
