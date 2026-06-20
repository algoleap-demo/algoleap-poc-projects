import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

class ProgressTracker:
    def __init__(self):
        self.subscribers = []

    async def stream(self):
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
             message: str = "",
             **kwargs):
        
        # Merge kwargs with defaults
        payload = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": kwargs.get("trace_id", ""),
            "span_id": kwargs.get("span_id", ""),
            "agent_name": agent_name,
            "agent_type": kwargs.get("agent_type", "RULE"), 
            "stage": kwargs.get("stage", "PLAN"),
            "decision": kwargs.get("decision", ""),
            "reason_summary": kwargs.get("reason_summary", ""),
            "inputs": kwargs.get("inputs", {}),
            "outputs": kwargs.get("outputs", {}),
            "tool_name": kwargs.get("tool_name", ""),
            "tool_status": kwargs.get("tool_status", ""),
            "confidence": kwargs.get("confidence", 1.0),
            "latency_ms": kwargs.get("latency_ms", 0),
            "status": status,
            "message": message 
        }
        
        event_str = f"data: {json.dumps(payload)}\n\n"
        for queue in self.subscribers:
            queue.put_nowait(event_str)

tracker = ProgressTracker()
