import asyncio
import os
import uuid
from typing import List, Optional, TypedDict

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

# Core Infrastructure
from app.core.progress_tracker import tracker
# Modular POC Orchestrators
from app.modules.planning.planning_orchestrator import run_account_planning
from app.modules.targeting.targeting_orchestrator import run_pipeline as run_targeting_pipeline
from app.modules.whitespace.whitespace_orchestrator import run_whitespace_pipeline

app = FastAPI(title="IQ-EQ Unified Agent Mesh")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class AnalyzeWhitespaceRequest(BaseModel):
    countries: Optional[List[str]] = None
    segment: Optional[str] = None
    product_ids: Optional[List[str]] = None


# Multi-Agent Mission State
class AgentState(TypedDict):
    filters: dict
    targeting_results: dict  # Result of POC1
    planning_results: dict  # Result of POC2
    whitespace_results: dict  # Result of POC3
    status: str
    run_id: str


# Node 1: Targeting & Triage (POC1)
async def targeting_node(state: AgentState):
    run_id = state.get("run_id") or str(uuid.uuid4())
    results = await run_targeting_pipeline(trace_id=run_id)
    mission_store["targeting_results"] = results
    return {"targeting_results": results, "status": "targeting_completed"}


# Node 2: Account Planning (POC2)
async def planning_node(state: AgentState):
    run_id = state.get("run_id")

    # Extract top accounts from POC1 results to seed POC2
    target_accounts = state["targeting_results"].get("accounts", [])
    top_account_ids = [acc["account_id"] for acc in target_accounts if acc["priority_bucket"] == "A"][:5]
    
    if not top_account_ids:
        tracker.emit("ag-orch", "warning", "No priority A accounts found. Using top 5 by propensity.", trace_id=run_id)
        top_account_ids = [acc["account_id"] for acc in sorted(target_accounts, key=lambda x: x["ml_score"], reverse=True)][:5]

    # Execute POC2 agents
    results = await run_account_planning({"account_ids": top_account_ids}, run_id=run_id)
    mission_store["planning_results"] = results
    return {"planning_results": results, "status": "planning_completed"}


async def whitespace_node(state: AgentState):
    run_id = state.get("run_id")
    results = await run_whitespace_pipeline(trace_id=run_id, embed_parent=True)
    mission_store["whitespace_results"] = results
    return {"whitespace_results": results, "status": "whitespace_completed"}


# Define the State Machine Graph
workflow = StateGraph(AgentState)
workflow.add_node("targeting", targeting_node)
workflow.add_node("planning", planning_node)
workflow.add_node("whitespace", whitespace_node)

workflow.set_entry_point("targeting")
workflow.add_edge("targeting", "planning")
workflow.add_edge("planning", "whitespace")
workflow.add_edge("whitespace", END)

# Compile the Mesh
mesh_app = workflow.compile()

# Global State Store for Demo Purposes
mission_store = {
    "targeting_results": {},
    "planning_results": {},
    "whitespace_results": {},
    "run_id": None,
}

# --- FastAPI Routes ---

@app.get("/")
async def serve_dashboard():
    """Serve SPA entrypoint here — do not mount StaticFiles at `/` or POST /run/* returns 405."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


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
        tracker.emit(
            "ag-orch",
            "START",
            "Unified Mission (POC 1→2→3). Live LLM/API pipelines — no dashboard mock data.",
            trace_id=run_id,
        )

        await mesh_app.ainvoke(
            {
                "run_id": run_id,
                "filters": {},
                "status": "started",
                "targeting_results": {},
                "planning_results": {},
                "whitespace_results": {},
            }
        )

        tracker.emit(
            "ag-orch",
            "END",
            "Unified Mission Lifecycle Complete (POC 1–3).",
            trace_id=run_id,
        )

    asyncio.create_task(run_task())
    return {"status": "unified_mission_initiated", "run_id": run_id}

@app.get("/mission_results")
async def get_mission_results():
    return {
        "targeting": mission_store["targeting_results"],
        "planning": mission_store["planning_results"],
        "whitespace": mission_store["whitespace_results"],
    }


@app.post("/run/poc1")
async def run_poc1():
    """Await POC1 targeting pipeline; streams progress via /events SSE."""
    run_id = str(uuid.uuid4())
    mission_store["run_id"] = run_id
    mission_store["targeting_results"] = {}
    mission_store["planning_results"] = {}
    mission_store["whitespace_results"] = {}
    results = await run_targeting_pipeline(trace_id=run_id)
    mission_store["targeting_results"] = results
    tracker.emit(
        "ag-orch",
        "END",
        "Targeting mission complete. Run Account Planning or full mesh when ready.",
        trace_id=run_id,
    )
    return results


@app.post("/run/poc2")
async def run_poc2():
    if not mission_store.get("targeting_results") or not mission_store["targeting_results"].get(
        "accounts"
    ):
        raise HTTPException(
            status_code=400, detail="Run Targeting first (/run/poc1)."
        )
    run_id = mission_store.get("run_id") or str(uuid.uuid4())
    mission_store["run_id"] = run_id
    target_accounts = mission_store["targeting_results"].get("accounts", [])
    top_account_ids = [
        acc["account_id"] for acc in target_accounts if acc["priority_bucket"] == "A"
    ][:5]
    if not top_account_ids:
        top_account_ids = [
            acc["account_id"]
            for acc in sorted(target_accounts, key=lambda x: x["ml_score"], reverse=True)
        ][:5]
    results = await run_account_planning({"account_ids": top_account_ids}, run_id=run_id)
    mission_store["planning_results"] = results
    tracker.emit(
        "ag-orch",
        "END",
        "Account Planning mission complete. Run Whitespace or full mesh when ready.",
        trace_id=run_id,
    )
    return results


@app.post("/run/poc3")
async def run_poc3(body: AnalyzeWhitespaceRequest = AnalyzeWhitespaceRequest()):
    run_id = mission_store.get("run_id") or str(uuid.uuid4())
    mission_store["run_id"] = run_id
    try:
        results = await run_whitespace_pipeline(
            trace_id=run_id,
            countries=body.countries,
            segment=body.segment,
            product_ids=body.product_ids,
            console=False,
            embed_parent=False,
        )
    except Exception as e:
        tracker.emit(
            "ag-orch",
            "FAILED",
            message=f"Whitespace mission failed: {e}",
            trace_id=run_id,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e
    mission_store["whitespace_results"] = results
    tracker.emit(
        "ag-orch",
        "END",
        "Whitespace mission complete.",
        trace_id=run_id,
    )
    return results


@app.post("/analyze_whitespace")
async def analyze_whitespace(body: AnalyzeWhitespaceRequest = AnalyzeWhitespaceRequest()):
    """POC3: full whitespace pipeline (grid, top accounts, campaign briefs, CSV path)."""
    return await run_whitespace_pipeline(
        countries=body.countries,
        segment=body.segment,
        product_ids=body.product_ids,
        console=False,
    )


# Static assets only (GET/HEAD). API POST routes stay on the main app above.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=False), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
