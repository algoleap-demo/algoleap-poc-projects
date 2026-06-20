from pydantic import BaseModel, Field
from typing import List, Optional

# Call Plan Item Model
class CallObjective(BaseModel):
    objective: str
    rationale: str

class CallAgendaItem(BaseModel):
    step: int
    topic: str
    key_question: str

# Single Account Planning Result Schema
class PlanningResult(BaseModel):
    account_id: str
    account_name: str
    contact_person: str
    brief_markdown: str
    objectives: List[CallObjective]
    agenda: List[CallAgendaItem]
    conflict_flag: bool = False

# Final Pipeline Response Schema
class PlanningPipelineResponse(BaseModel):
    pipeline_run_id: str
    generated_at: str
    model_version: str
    results: List[PlanningResult]

# --- Internal Agent Communication Schemas ---

# Brief Agent Output
class BriefOutput(BaseModel):
    account_id: str
    brief_markdown: str

# Call Plan Agent Output
class CallPlanOutput(BaseModel):
    account_id: str
    objectives: List[CallObjective]
    agenda: List[CallAgendaItem]
