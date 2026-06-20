import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from app.planning_orchestrator import run_account_planning
from app.progress_tracker import tracker
import asyncio
import json

app = FastAPI(title="IQ-EQ Agent Mesh - Account Planning")

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return {"message": "IQ-EQ Account Planning Agent API is running."}

@app.get("/events")
async def events():
    return StreamingResponse(tracker.stream(), media_type="text/event-stream")

@app.post("/run-planning")
async def run_pipeline_endpoint(filters: dict):
    # In a real POC, this would be a background task
    # For the interactive demo, we trigger it and the results are polled or sent via SSE
    asyncio.create_task(run_account_planning(filters))
    return {"status": "started", "message": "Planning lifecycle initiated."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) # Port 8001 to avoid conflict with POC1
