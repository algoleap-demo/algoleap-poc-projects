import uuid
import time
import json
import os
import hashlib
import asyncio
from datetime import datetime
from typing import Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.data_agent import run_data_agent
from app.agents.scoring_agent import run_scoring_agent
from app.agents.reasoning_agent import run_reasoning_agent
from app.agents.whitespace_agent import run_whitespace_agent
from app.agents.brief_agent import run_brief_agent
from app.agents.call_plan_agent import run_call_plan_agent
from app.agents.validation_agent import run_validation_agent
from app.agents.formatting_agent import run_formatting_agent
from app.progress_tracker import tracker
from app.llm_client import is_free_tier
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

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
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

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
async def scoring_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    
    # Skip if already cached
    if state["scoring_results"]:
        tracker.emit("ag-ml", "SKIPPED", "Targeting results identified in session cache. Bypassing ML scoring node.", trace_id=trace_id, agent_type="XGBoost", stage="PLAN")
        return state

    tracker.emit("ag-ml", "START", "Analyzing account propensity via XGBoost v1...", trace_id=trace_id, span_id=span_id, agent_type="XGBoost", stage="PLAN")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    scoring_results = run_scoring_agent(state["raw_data"])
    duration = time.time() - t0
    
    log_audit(trace_id, "scoring_agent", duration, state["raw_data"], scoring_results)
    tracker.emit("ag-ml", "END", "Machine learning inference complete.", trace_id=trace_id, span_id=span_id, agent_type="ML", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["ml_scoring"] = duration
    return {**state, "scoring_results": scoring_results, "telemetry": telemetry}

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=4, max=20))
async def reasoning_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())

    # Skip if already cached
    if state["reasoning_results"]:
        tracker.emit("ag-reason", "SKIPPED", "Contextual reasoning found in session cache. Bypassing LLM Reasoning node.", trace_id=trace_id, agent_type="LLM", stage="DECISION")
        return state

    if is_free_tier():
        tracker.emit("ag-reason", "INFO", "Free Tier Detection: Optimizing for Top 20 accounts to ensure daily quota stability.", trace_id=trace_id, agent_type="LLM", stage="DECISION")

    tracker.emit("ag-reason", "START", "Generating contextual rationales via OpenAI/OpenRouter...", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="DECISION")
    await asyncio.sleep(5.0)
    
    t0 = time.time()
    reasoning_results = await run_reasoning_agent(state["scoring_results"], state["raw_data"])
    duration = time.time() - t0
    
    log_audit(trace_id, "reasoning_agent", duration, {"scores": state["scoring_results"]}, reasoning_results)
    tracker.emit("ag-reason", "END", "Contextual reasoning generated.", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["reasoning"] = duration
    return {**state, "reasoning_results": reasoning_results, "telemetry": telemetry}

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
async def whitespace_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-ml", "START", "Analyzing product gaps and whitespace potential...", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="PLAN")
    
    t0 = time.time()
    planning_results = run_whitespace_agent(state["raw_data"])
    duration = time.time() - t0
    
    # Enrich planning_results with POC 1 context (scores/buckets)
    reasoning_map = {r["account_id"]: r for r in state["reasoning_results"]}
    scoring_map = {s["account_id"]: s for s in state["scoring_results"]}
    
    for p in planning_results:
        p["ml_score"] = scoring_map.get(p["account_id"], {}).get("propensity_score", 0.5)
        p["priority_bucket"] = reasoning_map.get(p["account_id"], {}).get("priority_bucket", "B")

    log_audit(trace_id, "whitespace_agent", duration, {"accounts": len(state["raw_data"].get("accounts", []))}, planning_results)
    tracker.emit("ag-ml", "END", "Whitespace analysis complete.", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["whitespace"] = duration
    return {**state, "planning_results": planning_results, "telemetry": telemetry}

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=4, max=20))
async def brief_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-brief", "START", "Generating high-fidelity account briefs via Gemini...", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="DECISION")
    
    t0 = time.time()
    # Verify online LLM connectivity
    try:
        planning_results = await run_brief_agent(state["planning_results"], state["raw_data"])
    except Exception as e:
        error_msg = f"CRITICAL: LLM Connectivity Interrupted during Briefing. {str(e)}"
        tracker.emit("ag-brief", "FAILED", message=error_msg, trace_id=trace_id, agent_type="LLM", stage="ERROR")
        raise
        
    duration = time.time() - t0
    
    log_audit(trace_id, "brief_agent", duration, {"input_planning": state["planning_results"]}, planning_results)
    tracker.emit("ag-brief", "END", "Account briefs generated.", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["briefing"] = duration
    return {**state, "planning_results": planning_results, "telemetry": telemetry}

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=4, max=20))
async def plan_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-plan", "START", "Crafting tactical discovery questions and call plans...", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="ACTION")
    
    t0 = time.time()
    planning_results = await run_call_plan_agent(state["planning_results"])
    duration = time.time() - t0
    
    log_audit(trace_id, "call_plan_agent", duration, {"briefs": [p.get("account_id") for p in state["planning_results"]]}, planning_results)
    tracker.emit("ag-plan", "END", "Tactical call plans finalized.", trace_id=trace_id, span_id=span_id, agent_type="LLM", stage="OUTPUT")
    
    telemetry = state.get("telemetry", {})
    telemetry["planning"] = duration
    return {**state, "planning_results": planning_results, "telemetry": telemetry}

async def validation_node(state: AgentMeshState) -> AgentMeshState:
    trace_id = state["trace_id"]
    span_id = str(uuid.uuid4())
    tracker.emit("ag-valid", "START", "Performing cross-agent conflict audits...", trace_id=trace_id, span_id=span_id, agent_type="RULE", stage="PLAN")
    await asyncio.sleep(2.0)
    
    t0 = time.time()
    validation_results = run_validation_agent(
        state["scoring_results"], 
        state["reasoning_results"], 
        trace_id,
        state.get("planning_results")
    )
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
        trace_id,
        state.get("planning_results") # Pass POC 2 data
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
    workflow.add_node("whitespace", whitespace_node)
    workflow.add_node("briefing", brief_node)
    workflow.add_node("planning", plan_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("formatting", formatting_node)
    
    workflow.set_entry_point("data_gathering")
    
    workflow.add_edge("data_gathering", "ml_scoring")
    workflow.add_edge("ml_scoring", "reasoning")
    
    # Conditional Branch based on POC selection
    def route_after_reasoning(state: AgentMeshState):
        if state["poc_id"] == 2:
            return "whitespace"
        return "validation"
        
    workflow.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {
            "whitespace": "whitespace",
            "validation": "validation"
        }
    )
    
    workflow.add_edge("whitespace", "briefing")
    workflow.add_edge("briefing", "planning")
    workflow.add_edge("planning", "validation")
    
    workflow.add_edge("validation", "formatting")
    workflow.add_edge("formatting", END)
    
    return workflow.compile(checkpointer=MemorySaver())

# --- Entry Point ---

async def run_pipeline(poc_id: int = 1, thread_id: str = "default-session"):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Orchestrator START
    tracker.emit("ag-orch", "START", f"Unified Mesh Pipeline initiated (POC {poc_id}). Trace: {trace_id}", trace_id=trace_id, agent_type="RULE", stage="PLAN")
    
    initial_state: AgentMeshState = {
        "trace_id": trace_id,
        "poc_id": poc_id,
        "raw_data": None,
        "scoring_results": [],
        "reasoning_results": [],
        "planning_results": [],
        "validation_results": [],
        "final_output": None,
        "errors": [],
        "telemetry": {}
    }
    
    try:
        graph = create_agent_mesh_graph()
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await graph.ainvoke(initial_state, config=config)
        
        total_duration = time.time() - start_time
        tracker.emit("ag-orch", "END", f"LangGraph Pipeline completed in {total_duration:.2f}s.", trace_id=trace_id, agent_type="RULE", stage="OUTPUT")
        
        return final_state["final_output"]
        
    except Exception as e:
        error_msg = f"LangGraph Pipeline failed: {str(e)}"
        tracker.emit("ag-orch", "FAILED", message=error_msg, trace_id=trace_id, agent_type="RULE", stage="ERROR")
        raise
