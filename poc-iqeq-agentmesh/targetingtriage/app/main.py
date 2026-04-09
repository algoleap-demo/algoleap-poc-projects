import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from app.orchestration_agent import run_pipeline
from app.progress_tracker import tracker
from pydantic import BaseModel

app = FastAPI(title="IQ-EQ Agent Mesh Dashboard")

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static and assets directories
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")), name="assets")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open(os.path.join(static_dir, "index.html"), "r") as f:
        return f.read()

@app.get("/events")
async def events(request: Request):
    return StreamingResponse(tracker.subscribe(), media_type="text/event-stream")

@app.post("/score_accounts")
async def score_accounts():
    # In a real app, this might be backgrounded, 
    # but for this demo, we run and return the final JSON.
    # The progress is streamed via /events simultaneously.
    result = await run_pipeline()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
