import uuid
import time
import json
import os
import hashlib
import asyncio
from datetime import datetime
from typing import Any
from app.modules.targeting.data_agent import run_data_agent
from app.modules.targeting.scoring_agent import run_scoring_agent
from app.modules.targeting.reasoning_agent import run_reasoning_agent
from app.modules.targeting.validation_agent import run_validation_agent
from app.modules.targeting.formatting_agent import run_formatting_agent
from app.core.progress_tracker import tracker
from app.core.pipeline_timing import AGENT_HANDOFF_DELAY_SEC
from app.core.audit_logger import log_audit

async def run_pipeline(trace_id: str = None):
    trace_id = trace_id or str(uuid.uuid4())
    start_time = time.time()
    
    # 0. Orchestrator START
    tracker.emit("ag-orch", "START", message=f"Pipeline initiated. Trace: {trace_id}", trace_id=trace_id, agent_type="RULE", stage="PLAN")
    await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

    try:
        # --- 1. Data Agent ---
        t0 = time.time()
        raw_data = run_data_agent(trace_id=trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "data_agent", duration, None, raw_data)
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        t0 = time.time()
        scoring_results = run_scoring_agent(raw_data, trace_id=trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "scoring_agent", duration, raw_data, scoring_results)
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        # --- 3. Reasoning Agent ---
        t0 = time.time()
        reasoning_results = await run_reasoning_agent(scoring_results, raw_data, trace_id=trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "reasoning_agent", duration, {"scores": scoring_results}, reasoning_results)
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        # --- 4. Validation Agent ---
        t0 = time.time()
        validation_results = run_validation_agent(scoring_results, reasoning_results, trace_id)
        duration = time.time() - t0
        
        log_audit(trace_id, "validation_agent", duration, {"scores": scoring_results}, validation_results)
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        # --- 5. Formatting Agent ---
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
        
        # 6. Final Orchestrator END
        total_duration = time.time() - start_time
        tracker.emit("ag-orch", "END", message=f"Pipeline completed in {total_duration:.2f}s.", trace_id=trace_id, agent_type="RULE", stage="OUTPUT")
        
        return final_response.dict()
        
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}"
        tracker.emit("ag-orch", "FAILED", message=error_msg, trace_id=trace_id, agent_type="RULE", stage="ERROR")
        raise
