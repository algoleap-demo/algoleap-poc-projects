from app.progress_tracker import tracker
from app.constants import NBA_RESOLUTION
from app.schemas import AccountResult, PipelineResponse, NBAAction
from datetime import datetime
import uuid

def run_formatting_agent(scoring_raw: list, reasoning_raw: list, validation_raw: list, full_raw: dict, model_version: str, run_id: str):
    tracker.emit("ag-fmt", "START", run_id, str(uuid.uuid4()), "API", "PLAN", message="Resolving account identities and NBA mappings...")
    
    # Map for easy assembly
    scoring_map = {r["account_id"]: r for r in scoring_raw}
    reasoning_map = {r["account_id"]: r for r in reasoning_raw}
    validation_map = {r["account_id"]: r for r in validation_raw}
    
    # Raw accounts for names
    accounts_df = full_raw["accounts"]
    accounts_map = accounts_df.set_index("account_id").to_dict(orient="index")
    
    account_results = []
    
    for acc_id in scoring_map.keys():
        s = scoring_map[acc_id]
        r = reasoning_map[acc_id]
        v = validation_map[acc_id]
        meta = accounts_map.get(acc_id, {"account_name": acc_id, "contact_person": "Unknown"})
        
        # Rule-based NBA resolution
        nba_data = NBA_RESOLUTION[r["priority_bucket"]]
        nba = NBAAction(
            action_type=nba_data["action_type"],
            description=nba_data["description"],
            reasoning=nba_data["reasoning"],
            due_in_days=nba_data["due_in_days"]
        )
        
        # Assemble AccountResult
        acc_res = AccountResult(
            account_id=acc_id,
            account_name=meta["account_name"],
            contact_person=meta["contact_person"],
            priority_bucket=r["priority_bucket"],
            ml_score=s["propensity_score"],
            confidence_level=s["confidence_level"],
            conflict_flag=v["conflict_flag"],
            rationale_text=r["rationale_text"],
            nba_actions=[nba]
        )
        account_results.append(acc_res)
        
    final_response = PipelineResponse(
        pipeline_run_id=run_id,
        generated_at=datetime.now().isoformat(),
        model_version=model_version,
        accounts=account_results
    )
    
    return final_response
