import uuid
import time
import json
import os
import hashlib
import asyncio
from datetime import datetime
from typing import Any
from app.agents.data_agent import run_data_agent
from app.agents.scoring_agent import run_scoring_agent
from app.agents.reasoning_agent import run_reasoning_agent
from app.agents.validation_agent import run_validation_agent
from app.agents.formatting_agent import run_formatting_agent
from app.progress_tracker import tracker

def get_hash(data: Any) -> str:
    try:
        if isinstance(data, dict):
            serializable = {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in data.items()}
        elif isinstance(data, list):
            serializable = data
        else:
            serializable = str(data)
        json_str = json.dumps(serializable, sort_keys=True, indent=None, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    except Exception:
        return "hash_error"

def log_audit(run_id: str, agent: str, duration: float, input_data: Any = None, output_data: Any = None):
    audit_path = "logs/audit.jsonl"
    os.makedirs("logs", exist_ok=True)
    entry = {
        "run_id": run_id,
        "agent": agent,
        "input_hash": get_hash(input_data),
        "output_hash": get_hash(output_data),
        "ts": datetime.now().isoformat(),
        "duration_ms": int(duration * 1000)
    }
    with open(audit_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

async def run_pipeline():
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 0. Orchestrator START
    tracker.emit("ag-orch", "START", trace_id, "", "RULE", "PLAN", message=f"Pipeline initiated. Trace: {trace_id}")
    await asyncio.sleep(5.0) # Show Orchestrator active
    
    try:
        # --- 1. Data Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-data", "START", trace_id, span_id, "API", "PLAN", message="Ingesting synthetic account data...")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        raw_data = run_data_agent()
        duration = time.time() - t0
        
        log_audit(trace_id, "data_agent", duration, None, raw_data)
        tracker.emit("ag-data", "END", trace_id, span_id, "API", "OUTPUT", message=f"Data ingestion complete. {len(raw_data)} accounts loaded.")

        # --- 2. Scoring Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-ml", "START", trace_id, span_id, "ML", "ACTION", message="Executing XGBoost propensity scoring...")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        scoring_results = run_scoring_agent(raw_data)
        duration = time.time() - t0
        
        log_audit(trace_id, "scoring_agent", duration, raw_data, scoring_results)
        tracker.emit("ag-ml", "END", trace_id, span_id, "ML", "OUTPUT", message="Machine learning inference complete.")

        # --- 3. Reasoning Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-reason", "START", trace_id, span_id, "LLM", "DECISION", message="Analyzing contextual catalysts via LLM...")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        reasoning_results = await run_reasoning_agent(scoring_results, raw_data)
        duration = time.time() - t0
        
        log_audit(trace_id, "reasoning_agent", duration, {"scores": scoring_results}, reasoning_results)
        tracker.emit("ag-reason", "END", trace_id, span_id, "LLM", "OUTPUT", message="Contextual reasoning generated.")

        # --- 4. Validation Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-valid", "START", trace_id, span_id, "RULE", "PLAN", message="Performing cross-agent conflict audits...")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        validation_results = run_validation_agent(scoring_results, reasoning_results, trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "validation_agent", duration, {"scores": scoring_results}, validation_results)
        tracker.emit("ag-valid", "END", trace_id, span_id, "RULE", "OUTPUT", message="Validation audit complete.")

        # --- 5. Formatting Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-fmt", "START", trace_id, span_id, "API", "ACTION", message="Resolving NBAs and formatting final payload...")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        final_response = run_formatting_agent(
            scoring_results, 
            reasoning_results, 
            validation_results,
            raw_data,
            "xgb_propensity_v1", 
            trace_id
        )
        duration = time.time() - t0
        
        log_audit(trace_id, "formatting_agent", duration, {"v": validation_results}, final_response.dict())
        tracker.emit("ag-fmt", "END", trace_id, span_id, "API", "OUTPUT", message="Final output validated and formatted.")
        
        # 6. Final Orchestrator END
        total_duration = time.time() - start_time
        tracker.emit("ag-orch", "END", trace_id, "", "RULE", "OUTPUT", message=f"Pipeline completed in {total_duration:.2f}s.")
        
        return final_response.dict()
        
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}"
        tracker.emit("ag-orch", "FAILED", trace_id, "", "RULE", "ERROR", message=error_msg)
        raise
