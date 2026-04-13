import json
import os
from datetime import datetime
from app.core.progress_tracker import tracker
from app.core.constants import ML_HIGH_THRESHOLD, ML_LOW_THRESHOLD, LLM_BUCKET_TO_LEVEL

def run_validation_agent(scoring_results: list, reasoning_results: list, run_id: str):
    tracker.emit("ag-valid", "started", message="Running cross-agent conflict validation...", trace_id=run_id)
    
    # Map reasoning results for easy lookup
    reasoning_map = {r["account_id"]: r for r in reasoning_results}
    results = []
    conflicts_found = 0
    
    gov_log_path = "logs/governance_queue.jsonl"
    os.makedirs("logs", exist_ok=True)
    
    with open(gov_log_path, "a") as gov_file:
        for s_res in scoring_results:
            acc_id = s_res["account_id"]
            llm_res = reasoning_map[acc_id]
            
            ml_score = s_res["propensity_score"]
            llm_bucket = llm_res["priority_bucket"]
            
            # Conflict Logic
            ml_level = "High" if ml_score >= ML_HIGH_THRESHOLD else \
                       "Low"  if ml_score <= ML_LOW_THRESHOLD  else "Medium"
            llm_level = LLM_BUCKET_TO_LEVEL[llm_bucket]
            
            is_conflict = (ml_level, llm_level) in {("High", "Low"), ("Low", "High")}
            
            if is_conflict:
                conflicts_found += 1
                tracker.emit("ag-valid", "warning", message=f"Conflict detected on {acc_id}: ML={ml_level}, LLM={llm_level}")
                
                # Append to governance queue
                gov_entry = {
                    "run_id": run_id,
                    "account_id": acc_id,
                    "ml_score": ml_score,
                    "ml_level": ml_level,
                    "llm_bucket": llm_bucket,
                    "llm_level": llm_level,
                    "conflict_flag": True,
                    "timestamp": datetime.now().isoformat()
                }
                gov_file.write(json.dumps(gov_entry) + "\n")
                
            results.append({
                "account_id": acc_id,
                "conflict_flag": is_conflict
            })
            
    tracker.emit("ag-valid", "completed", message=f"Validation complete. {conflicts_found} conflicts surfaced and logged to governance queue.")
    return results
