import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

class ProgressTracker:
    def __init__(self):
        self.subscribers = []

    async def subscribe(self):
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self.subscribers.remove(queue)

    def emit(self, 
             agent_name: str, 
             status: str, 
             trace_id: str = "",
             span_id: str = "",
             agent_type: str = "RULE",
             stage: str = "PLAN",
             decision: str = "",
             reason_summary: str = "",
             inputs: Dict[str, Any] = None,
             outputs: Dict[str, Any] = None,
             tool_name: str = "",
             tool_status: str = "",
             confidence: float = 1.0,
             latency_ms: int = 0,
             message: str = ""):
        
        # Construct the requested structured log
        payload = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "span_id": span_id,
            "agent_name": agent_name,
            "agent_type": agent_type, # LLM | ML | RULE | API
            "stage": stage, # PLAN | DECISION | ACTION | TOOL | OUTPUT | ERROR
            "decision": decision,
            "reason_summary": reason_summary,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "tool_name": tool_name,
            "tool_status": tool_status, # SUCCESS | FAILED
            "confidence": confidence,
            "latency_ms": latency_ms,
            "status": status, # START | IN_PROGRESS | END | FAILED
            "message": message # For UI backwards compatibility
        }
        
        event_str = f"data: {json.dumps(payload)}\n\n"
        for queue in self.subscribers:
            queue.put_nowait(event_str)

tracker = ProgressTracker()
