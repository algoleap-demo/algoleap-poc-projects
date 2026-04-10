import json
import os
from datetime import datetime
from app.core.progress_tracker import tracker

def run_validation_agent(briefs: list, raw_data: dict):
    tracker.emit("ag-valid", "started", message="Targeting Planning Validation: Auditing brief integrity...")
    
    results = []
    issues_found = 0
    
    for b in briefs:
        acc_id = b["account_id"]
        brief_text = b.get("brief_markdown", "")
        
        # Simple Validation: Brief must be at least 100 characters
        is_valid = len(brief_text) > 100
        
        if not is_valid:
            issues_found += 1
            tracker.emit("ag-valid", "warning", message=f"Brief integrity warning on {acc_id}: Content too short.")
            
        results.append({
            "account_id": acc_id,
            "conflict_flag": not is_valid # Reusing 'conflict_flag' for UI compatibility
        })
            
    tracker.emit("ag-valid", "completed", message=f"Planning validation complete. {issues_found} potential quality issues flagged.")
    return results
