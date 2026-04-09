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
    tracker.emit("ag-orch", "START", f"Pipeline initiated. Trace: {trace_id}", trace_id=trace_id, agent_type="RULE", stage="PLAN")
    await asyncio.sleep(5.0) # Show Orchestrator active
    
    try:
        # --- 1. Data Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-data", "START", "Ingesting synthetic account data...", trace_id=trace_id, span_id=span_id, agent_type="API", stage="PLAN")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        raw_data = run_data_agent()
        duration = time.time() - t0
        
        log_audit(trace_id, "data_agent", duration, None, raw_data)
        tracker.emit("ag-data", "END", f"Data ingestion complete. {len(raw_data)} accounts loaded.", trace_id=trace_id, span_id=span_id, agent_type="API", stage="OUTPUT")

        # --- 2. Scoring Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-ml", "START", "Executing XGBoost propensity scoring...", trace_id=trace_id, span_id=span_id, agent_type="ML", stage="ACTION")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        scoring_results = run_scoring_agent(raw_data)
        duration = time.time() - t0
        
        log_audit(trace_id, "scoring_agent", duration, raw_data, scoring_results)
        tracker.emit("ag-ml", "END", "Machine learning inference complete.", trace_id=trace_id, span_id=span_id, agent_type="ML", stage="OUTPUT")

        # --- 3. Reasoning Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-reason", "START", "Analyzing contextual catalysts via LLM...", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="DECISION")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        reasoning_results = await run_reasoning_agent(scoring_results, raw_data)
        duration = time.time() - t0
        
        log_audit(trace_id, "reasoning_agent", duration, {"scores": scoring_results}, reasoning_results)
        tracker.emit("ag-reason", "END", "Contextual reasoning generated.", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="OUTPUT")

        # --- 4. Validation Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-valid", "START", "Performing cross-agent conflict audits...", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="PLAN")
        await asyncio.sleep(5.0) # STAY YELLOW for 5s
        
        t0 = time.time()
        validation_results = run_validation_agent(scoring_results, reasoning_results, trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "validation_agent", duration, {"scores": scoring_results}, validation_results)
        tracker.emit("ag-valid", "END", "Validation audit complete.", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="OUTPUT")

        # --- 5. Formatting Agent ---
        span_id = str(uuid.uuid4())
        tracker.emit("ag-fmt", "START", "Resolving NBAs and formatting final payload...", trace_id=trace_id, span_id=span_id, agent_type="API", stage="ACTION")
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
        tracker.emit("ag-fmt", "END", "Final output validated and formatted.", trace_id=trace_id, span_id=span_id, agent_type="API", stage="OUTPUT")
        
        # 6. Final Orchestrator END
        total_duration = time.time() - start_time
        tracker.emit("ag-orch", "END", f"Pipeline completed in {total_duration:.2f}s.", trace_id=trace_id, agent_type="RULE", stage="OUTPUT")
        
        return final_response.dict()
        
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}"
        tracker.emit("ag-orch", "FAILED", trace_id, "", "RULE", "ERROR", message=error_msg)
        raise
