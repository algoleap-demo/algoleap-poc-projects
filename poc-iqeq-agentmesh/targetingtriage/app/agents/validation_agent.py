import json
import os
from datetime import datetime
from app.progress_tracker import tracker
from app.constants import ML_HIGH_THRESHOLD, ML_LOW_THRESHOLD, LLM_BUCKET_TO_LEVEL

def run_validation_agent(scoring_results: list, reasoning_results: list, run_id: str, whitespace_results: list = None):
    tracker.emit("ag-valid", "started", message="Running cross-agent conflict validation...")
    
    # Map reasoning and whitespace results for easy lookup
    reasoning_map = {r["account_id"]: r for r in reasoning_results}
    whitespace_map = {w["account_id"]: w for w in whitespace_results} if whitespace_results else {}
    
    results = []
    conflicts_found = 0
    
    gov_log_path = "logs/governance_queue.jsonl"
    os.makedirs("logs", exist_ok=True)
    
    with open(gov_log_path, "a") as gov_file:
        for s_res in scoring_results:
            acc_id = s_res["account_id"]
            llm_res = reasoning_map[acc_id]
            ws_res = whitespace_map.get(acc_id)
            
            ml_score = s_res["propensity_score"]
            llm_bucket = llm_res["priority_bucket"]
            
            # --- Conflict 1: Triage Gaps (ML vs LLM) ---
            ml_level = "High" if ml_score >= ML_HIGH_THRESHOLD else \
                       "Low"  if ml_score <= ML_LOW_THRESHOLD  else "Medium"
            llm_level = LLM_BUCKET_TO_LEVEL[llm_bucket]
            
            is_triage_conflict = (ml_level, llm_level) in {("High", "Low"), ("Low", "High")}
            
            # --- Conflict 2: Hidden Gem (Whitespace vs Bucket) ---
            is_hidden_gem = False
            if ws_res and llm_bucket == "C" and ws_res["total_ws_potential_eur"] >= 1000000:
                is_hidden_gem = True
            
            is_conflict = is_triage_conflict or is_hidden_gem
            
            if is_conflict:
                conflicts_found += 1
                reason = "Triage Gap" if is_triage_conflict else "Hidden Gem"
                tracker.emit("ag-valid", "warning", message=f"Conflict ({reason}) detected on {acc_id}")
                
                # Append to governance queue
                gov_entry = {
                    "run_id": run_id,
                    "account_id": acc_id,
                    "ml_score": ml_score,
                    "llm_bucket": llm_bucket,
                    "ws_potential": int(ws_res["total_ws_potential_eur"]) if ws_res else 0,
                    "conflict_type": reason,
                    "timestamp": datetime.now().isoformat()
                }
                gov_file.write(json.dumps(gov_entry) + "\n")
                
            results.append({
                "account_id": acc_id,
                "conflict_flag": is_conflict,
                "conflict_type": "None" if not is_conflict else ("Triage Gap" if is_triage_conflict else "Hidden Gem")
            })
            
    tracker.emit("ag-valid", "completed", message=f"Validation complete. {conflicts_found} conflicts surfaced and logged to governance queue.")
    return results
