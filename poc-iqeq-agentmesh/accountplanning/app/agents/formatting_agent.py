from app.progress_tracker import tracker
from app.schemas import PlanningResult, PlanningPipelineResponse, CallObjective, CallAgendaItem
from datetime import datetime
import uuid

async def run_formatting_agent(briefs: list, call_plans: list, validations: list, raw_data: dict):
    tracker.emit("ag-fmt", "started", message="Consolidating Account Planning packages...")
    
    accounts_df = raw_data["accounts"]
    accounts_map = {row.account_id: row for _, row in accounts_df.iterrows()}
    
    brief_map = {b["account_id"]: b for b in briefs}
    plan_map = {p["account_id"]: p for p in call_plans}
    valid_map = {v["account_id"]: v for v in validations}
    
    results = []
    for acc_id in brief_map.keys():
        meta = accounts_map.get(acc_id)
        b = brief_map[acc_id]
        p = plan_map[acc_id]
        v = valid_map.get(acc_id, {"conflict_flag": False})
        
        # Build PlanningResult
        res = PlanningResult(
            account_id=acc_id,
            account_name=meta["account_name"] if meta is not None else acc_id,
            contact_person=meta["contact_person"] if meta is not None else "Unknown",
            brief_markdown=b["brief_markdown"],
            objectives=p["objectives"],
            agenda=p["agenda"],
            conflict_flag=v["conflict_flag"]
        )
        results.append(res)
        
    response = PlanningPipelineResponse(
        pipeline_run_id=str(uuid.uuid4()),
        generated_at=datetime.now().isoformat(),
        model_version="iqmesh_planning_v1",
        results=results
    )
    
    tracker.emit("ag-fmt", "completed", message=f"Account Planning Response finalized for {len(results)} accounts.")
    return response.dict()
