import json
import os
import hashlib
from datetime import datetime
from typing import Any

def get_hash(data: Any) -> str:
    """
    Computes a SHA-256 hash of the input data for audit integrity.
    """
    try:
        if data is None:
            return None
        # Handle Pydantic models if they have a dict() or model_dump() method
        if hasattr(data, "model_dump"):
            serializable = data.model_dump()
        elif hasattr(data, "dict"):
            serializable = data.dict()
        elif isinstance(data, dict):
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
    """
    Writes an audit entry to logs/audit.jsonl.
    """
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

def log_governance_conflict(run_id: str, account_id: str, conflict_type: str, details: str):
    """
    Writes a governance conflict entry to logs/governance_queue.jsonl.
    """
    gov_path = "logs/governance_queue.jsonl"
    os.makedirs("logs", exist_ok=True)
    
    entry = {
        "run_id": run_id,
        "account_id": account_id,
        "conflict_type": conflict_type,
        "details": details,
        "ts": datetime.now().isoformat(),
        "status": "pending_review"
    }
    
    with open(gov_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_poc3_governance_flag(
    run_id: str,
    account_id: str,
    product_id: str,
    flag_type: str,
    anomaly_note: str,
):
    """POC3 validation flags appended to governance_queue (§03.5)."""
    gov_path = "logs/governance_queue.jsonl"
    os.makedirs("logs", exist_ok=True)
    entry = {
        "run_id": run_id,
        "account_id": account_id,
        "product_id": product_id,
        "flag_type": flag_type,
        "anomaly_note": anomaly_note,
        "ts": datetime.now().isoformat(),
        "status": "pending_review",
    }
    with open(gov_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
