import time
import uuid
from app.modules.planning.data_agent import run_data_agent
from app.modules.planning.whitespace_agent import run_whitespace_agent
from app.modules.planning.brief_agent import run_brief_agent
from app.modules.planning.validation_agent import run_validation_agent
from app.modules.planning.formatting_agent import run_formatting_agent
from app.core.progress_tracker import tracker
from app.core.audit_logger import log_audit


async def run_account_planning(filters: dict, run_id: str = None):
    trace_id = run_id or str(uuid.uuid4())
    tracker.emit(
        "ag-orch",
        "started",
        message="Initiating Account Planning Mesh Lifecycle...",
        trace_id=trace_id,
    )

    t0 = time.time()
    raw_data = run_data_agent(trace_id=trace_id)
    duration = time.time() - t0
    log_audit(trace_id, "data_agent", duration, None, {"tables": list(raw_data.keys())})

    accounts = filters.get("account_ids", [])
    if not accounts:
        accounts = raw_data["accounts"]["account_id"].tolist()[:5]

    tracker.emit(
        "ag-orch",
        "processing",
        message=f"Targeting {len(accounts)} accounts for strategic intelligence...",
        trace_id=trace_id,
    )

    t0 = time.time()
    scoring_rows = run_whitespace_agent(raw_data, accounts, trace_id=trace_id)
    duration = time.time() - t0
    log_audit(trace_id, "whitespace_agent", duration, {"accounts": accounts}, scoring_rows)

    t0 = time.time()
    brief_results = await run_brief_agent(
        accounts, raw_data, scoring_rows, trace_id=trace_id
    )
    duration = time.time() - t0
    log_audit(trace_id, "account_brief_agent", duration, {"accounts": accounts}, brief_results)

    score_by_id = {r["account_id"]: r for r in scoring_rows}
    t0 = time.time()
    validations = run_validation_agent(brief_results, score_by_id, trace_id=trace_id)
    duration = time.time() - t0
    log_audit(trace_id, "validation_agent", duration, {"accounts": accounts}, validations)

    t0 = time.time()
    final_payload = await run_formatting_agent(
        brief_results,
        validations,
        scoring_rows,
        raw_data=raw_data,
        trace_id=trace_id,
    )
    duration = time.time() - t0
    log_audit(trace_id, "formatting_agent", duration, {"accounts": accounts}, final_payload)

    tracker.emit(
        "ag-orch",
        "completed",
        message=f"Account Planning Mesh Lifecycle Complete for {len(accounts)} accounts.",
        trace_id=trace_id,
    )
    return final_payload
