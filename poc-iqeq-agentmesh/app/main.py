import asyncio
import os
import uuid
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Core Infrastructure
from app.core.progress_tracker import tracker
# Modular POC Orchestrators
from app.modules.targeting.targeting_orchestrator import run_pipeline as run_targeting_pipeline
from app.modules.planning.planning_orchestrator import run_account_planning

app = FastAPI(title="IQ-EQ Unified Agent Mesh")

# Multi-Agent Mission State
class AgentState(TypedDict):
    filters: dict
    targeting_results: dict # Result of POC1
    planning_results: dict  # Result of POC2
    status: str
    run_id: str

# Node 1: Targeting & Triage (POC1)
async def targeting_node(state: AgentState):
    run_id = state.get("run_id") or str(uuid.uuid4())
    tracker.emit("ag-orch", "START", "Phase 1: Multi-Agent Targeting & Triage initiated.", trace_id=run_id)
    results = await run_targeting_pipeline(trace_id=run_id) 
    mission_store["targeting_results"] = results # Direct store
    return {"targeting_results": results, "status": "targeting_completed"}

# Node 2: Account Planning (POC2)
async def planning_node(state: AgentState):
    run_id = state.get("run_id")
    tracker.emit("ag-orch", "START", "Phase 2: Transitioning to Account Planning logic.", trace_id=run_id)
    
    # Extract top accounts from POC1 results to seed POC2
    target_accounts = state["targeting_results"].get("accounts", [])
    top_account_ids = [acc["account_id"] for acc in target_accounts if acc["priority_bucket"] == "A"][:5]
    
    if not top_account_ids:
        tracker.emit("ag-orch", "warning", "No priority A accounts found. Using top 5 by propensity.", trace_id=run_id)
        top_account_ids = [acc["account_id"] for acc in sorted(target_accounts, key=lambda x: x["ml_score"], reverse=True)][:5]

    # Execute POC2 agents
    results = await run_account_planning({"account_ids": top_account_ids}, run_id=run_id)
    mission_store["planning_results"] = results # Direct store
    return {"planning_results": results, "status": "mission_completed"}

# Define the State Machine Graph
workflow = StateGraph(AgentState)
workflow.add_node("targeting", targeting_node)
workflow.add_node("planning", planning_node)

workflow.set_entry_point("targeting")
workflow.add_edge("targeting", "planning")
workflow.add_edge("planning", END)

# Compile the Mesh
mesh_app = workflow.compile()

# Global State Store for Demo Purposes
mission_store = {
    "targeting_results": {},
    "planning_results": {},
    "run_id": None
}

# --- FastAPI Routes ---

@app.get("/events")
async def events():
    return StreamingResponse(tracker.stream(), media_type="text/event-stream")

@app.post("/score_accounts")
async def score_accounts():
    run_id = str(uuid.uuid4())
    mission_store["run_id"] = run_id
    
    async def run_task():
        tracker.emit("ag-orch", "START", "Phase 1: Multi-Agent Targeting & Triage initiated.")
        results = await run_targeting_pipeline()
        mission_store["targeting_results"] = results
        tracker.emit("ag-orch", "END", "Targeting Phase Complete. Manual Planning Gate Unlocked.")

    asyncio.create_task(run_task())
    return {"status": "targeting_initiated", "run_id": run_id}

@app.post("/plan_accounts")
async def plan_accounts():
    if not mission_store["targeting_results"]:
        return {"status": "error", "message": "Targeting results not found. Please run Targeting first."}

    tracker.emit("ag-orch", "START", "Phase 2: Transitioning to Account Planning logic.")
    target_accounts = mission_store["targeting_results"].get("accounts", [])
    top_account_ids = [
        acc["account_id"] for acc in target_accounts if acc["priority_bucket"] == "A"
    ][:5]

    if not top_account_ids:
        top_account_ids = [
            acc["account_id"]
            for acc in sorted(target_accounts, key=lambda x: x["ml_score"], reverse=True)
        ][:5]

    results = await run_account_planning(
        {"account_ids": top_account_ids}, run_id=mission_store["run_id"]
    )
    mission_store["planning_results"] = results
    tracker.emit(
        "ag-orch",
        "END",
        "Account Planning Mesh Lifecycle Complete.",
        trace_id=mission_store["run_id"],
    )
    return results

@app.post("/execute_mission")
async def execute_mission():
    run_id = str(uuid.uuid4())
    mission_store["run_id"] = run_id
    
    async def run_task():
        tracker.emit("ag-orch", "START", "Unified Mission Lifecycle Initiated (End-to-End).", trace_id=run_id)
        
        # Invoke the LangGraph StateGraph (targeting -> planning)
        final_state = await mesh_app.ainvoke({
            "run_id": run_id,
            "filters": {},
            "status": "started"
        })
        
        # mission_store is already updated by the nodes
        
        tracker.emit("ag-orch", "END", "Unified Mission Lifecycle Complete.", trace_id=run_id)

    asyncio.create_task(run_task())
    return {"status": "unified_mission_initiated", "run_id": run_id}

@app.get("/mission_results")
async def get_mission_results():
    return {
        "targeting": mission_store["targeting_results"],
        "planning": mission_store["planning_results"]
    }

# Mount UI
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
