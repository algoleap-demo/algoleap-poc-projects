import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.orchestration_agent import run_pipeline
from app.progress_tracker import tracker
from tenacity import RetryError
import openai

app = FastAPI(title="IQ-EQ Agent Mesh Dashboard")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Unwrap Tenacity RetryErrors to find the root cause (e.g., RateLimitError)
    root_exc = exc
    if isinstance(exc, RetryError):
        root_exc = exc.last_attempt.exception() if hasattr(exc, 'last_attempt') else exc

    if isinstance(root_exc, openai.RateLimitError):
        return JSONResponse(status_code=429, content={"detail": "Rate Limit Exceeded"})
    if isinstance(root_exc, openai.APIStatusError):
        if root_exc.status_code == 402:
            return JSONResponse(status_code=402, content={"detail": "Payment Required"})
        if root_exc.status_code == 401:
            return JSONResponse(status_code=401, content={"detail": "Authentication Failed"})
        return JSONResponse(status_code=root_exc.status_code, content={"detail": str(root_exc)})
    
    return JSONResponse(status_code=500, content={"detail": str(exc)})

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
    # In a production app, this would be a session or cookie ID
    result = await run_pipeline(thread_id="demo-session-001")
    return result

@app.post("/plan_accounts")
async def plan_accounts():
    # Use the same thread_id to resume from Triage state
    result = await run_pipeline(poc_id=2, thread_id="demo-session-001")
    return result

@app.post("/analyze_whitespace")
async def analyze_whitespace():
    # Placeholder for POC 3
    return {"message": "Whitespace export generated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
