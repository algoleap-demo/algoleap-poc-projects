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
from app.core.llm_client import llm

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
    tracker.emit("ag-orch", "START", "Phase 1: Multi-Agent Targeting & Triage initiated.")
    results = await run_targeting_pipeline() # Calls the 6-agent POC1 loop
    return {"targeting_results": results, "status": "targeting_completed"}

# Node 2: Account Planning (POC2)
async def planning_node(state: AgentState):
    tracker.emit("ag-orch", "START", "Phase 2: Transitioning to Account Planning logic.")
    
    # Extract top accounts from POC1 results to seed POC2
    target_accounts = state["targeting_results"].get("accounts", [])
    top_account_ids = [acc["account_id"] for acc in target_accounts if acc["priority_bucket"] == "A"][:5]
    
    if not top_account_ids:
        tracker.emit("ag-orch", "warning", "No priority A accounts found. Using top 5 by propensity.")
        top_account_ids = [acc["account_id"] for acc in sorted(target_accounts, key=lambda x: x["ml_score"], reverse=True)][:5]

    # Execute POC2 agents
    results = await run_account_planning({"account_ids": top_account_ids})
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

# --- FastAPI Routes ---

@app.get("/events")
async def events():
    return StreamingResponse(tracker.stream(), media_type="text/event-stream")

@app.post("/run-mission")
async def run_mission(filters: dict):
    run_id = str(uuid.uuid4())
    initial_state = {
        "filters": filters, 
        "targeting_results": {}, 
        "planning_results": {}, 
        "status": "started",
        "run_id": run_id
    }
    # Run the graph in background
    asyncio.create_task(mesh_app.ainvoke(initial_state))
    return {"status": "mission_initiated", "run_id": run_id}

# Mount UI
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
