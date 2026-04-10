import uuid
import time
import json
import os
import hashlib
import asyncio
from datetime import datetime
from typing import Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.data_agent import run_data_agent
from app.agents.scoring_agent import run_scoring_agent
from app.agents.reasoning_agent import run_reasoning_agent
from app.agents.validation_agent import run_validation_agent
from app.agents.formatting_agent import run_formatting_agent
from app.progress_tracker import tracker
from app.schemas import AgentMeshState

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

# --- LangGraph Nodes ---

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def data_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-data", "START", "Ingesting synthetic account data...", trace_id=trace_id, span_id=span_id, agent_type="API", stage="PLAN")
    await asyncio.sleep(5.0) 
    
    t0 = time.time()
    raw_data = run_data_agent()
    duration = time.time() - t0
    
    log_audit(trace_id, "data_agent", duration, None, raw_data)
    tracker.emit("ag-data", "END", f"Data ingestion complete. {len(raw_data['accounts'])} accounts loaded.", trace_id=trace_id, span_id=span_id, agent_type="API", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["data_gathering"] = duration
    return {**state, "raw_data": raw_data, "telemetry": telemetry}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def scoring_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-ml", "START", "Executing XGBoost propensity scoring...", trace_id=trace_id, span_id=span_id, agent_type="ML", stage="ACTION")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    scoring_results = run_scoring_agent(state["raw_data"])
    duration = time.time() - t0
    
    log_audit(trace_id, "scoring_agent", duration, state["raw_data"], scoring_results)
    tracker.emit("ag-ml", "END", "Machine learning inference complete.", trace_id=trace_id, span_id=span_id, agent_type="ML", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["ml_scoring"] = duration
    return {**state, "scoring_results": scoring_results, "telemetry": telemetry}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
async def reasoning_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-reason", "START", "Analyzing contextual catalysts via LangChain (with Retries)...", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="DECISION")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    reasoning_results = await run_reasoning_agent(state["scoring_results"], state["raw_data"])
    duration = time.time() - t0
    
    log_audit(trace_id, "reasoning_agent", duration, {"scores": state["scoring_results"]}, reasoning_results)
    tracker.emit("ag-reason", "END", "Contextual reasoning generated.", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["reasoning"] = duration
    return {**state, "reasoning_results": reasoning_results, "telemetry": telemetry}

async def validation_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-valid", "START", "Performing cross-agent conflict audits...", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="PLAN")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    validation_results = run_validation_agent(state["scoring_results"], state["reasoning_results"], trace_id)
    duration = time.time() - t0
    
    log_audit(trace_id, "validation_agent", duration, {"scores": state["scoring_results"]}, validation_results)
    tracker.emit("ag-valid", "END", "Validation audit complete.", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["validation"] = duration
    return {**state, "validation_results": validation_results, "telemetry": telemetry}

async def formatting_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-fmt", "START", "Resolving NBAs and formatting final payload...", trace_id=trace_id, span_id=span_id, agent_type="API", stage="ACTION")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    final_response = run_formatting_agent(
        state["scoring_results"], 
        state["reasoning_results"], 
        state["validation_results"],
        state["raw_data"],
        "xgb_propensity_v1", 
        trace_id
    )
    duration = time.time() - t0
    
    log_audit(trace_id, "formatting_agent", duration, {"v": state["validation_results"]}, final_response.dict())
    tracker.emit("ag-fmt", "END", "Final output validated and formatted.", trace_id=trace_id, span_id=span_id, agent_type="API", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["formatting"] = duration
    return {**state, "final_output": final_response.dict(), "telemetry": telemetry}

# --- Graph Definition ---

def create_agent_mesh_graph():
    workflow = StateGraph(AgentMeshState)
    
    workflow.add_node("data_gathering", data_node)
    workflow.add_node("ml_scoring", scoring_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("formatting", formatting_node)
    
    workflow.set_entry_point("data_gathering")
    
    workflow.add_edge("data_gathering", "ml_scoring")
    workflow.add_edge("ml_scoring", "reasoning")
    workflow.add_edge("reasoning", "validation")
    workflow.add_edge("validation", "formatting")
    workflow.add_edge("formatting", END)
    
    return workflow.compile()

# --- Entry Point ---

async def run_pipeline():
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Orchestrator START
    tracker.emit("ag-orch", "START", f"LangGraph Pipeline initiated. Trace: {trace_id}", trace_id=trace_id, agent_type="RULE", stage="PLAN")
    
    initial_state: AgentMeshState = {
        "trace_id": trace_id,
        "raw_data": None,
        "scoring_results": [],
        "reasoning_results": [],
        "validation_results": [],
        "final_output": None,
        "errors": [],
        "telemetry": {}
    }
    
    try:
        graph = create_agent_mesh_graph()
        final_state = await graph.ainvoke(initial_state)
        
        total_duration = time.time() - start_time
        tracker.emit("ag-orch", "END", f"LangGraph Pipeline completed in {total_duration:.2f}s.", trace_id=trace_id, agent_type="RULE", stage="OUTPUT")
        
        return final_state["final_output"]
        
    except Exception as e:
        error_msg = f"LangGraph Pipeline failed: {str(e)}"
        tracker.emit("ag-orch", "FAILED", message=error_msg, trace_id=trace_id, agent_type="RULE", stage="ERROR")
        raise
