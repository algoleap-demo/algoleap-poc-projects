import asyncio

from app.agents.data_agent import run_data_agent
from app.agents.brief_agent import run_brief_agent
from app.agents.call_plan_agent import run_call_plan_agent
from app.agents.formatting_agent import run_formatting_agent
from app.progress_tracker import tracker


async def run_account_planning(filters: dict):
    tracker.emit("ag-orch", "started", message="Initiating Account Planning (standalone service)...")

    raw_data = run_data_agent()
    accounts = (filters or {}).get("account_ids")
    if not accounts:
        accounts = raw_data["accounts"].account_id.tolist()[:5]
    else:
        accounts = list(accounts)[:5]

    tracker.emit("ag-orch", "processing", message="Running brief and call-plan agents...")
    briefs, call_plans = await asyncio.gather(
        run_brief_agent(accounts, raw_data),
        run_call_plan_agent(accounts, raw_data),
    )

    validations = [
        {
            "account_id": b["account_id"],
            "conflict_flag": len(b.get("brief_markdown", "")) < 50,
        }
        for b in briefs
    ]

    final_payload = await run_formatting_agent(briefs, call_plans, validations, raw_data)

    tracker.emit("ag-orch", "completed", message="Account Planning Lifecycle Complete.")
    return final_payload
