import asyncio
from app.modules.planning.data_agent import run_data_agent
from app.modules.planning.brief_agent import run_brief_agent
from app.modules.planning.call_plan_agent import run_call_plan_agent
from app.modules.planning.validation_agent import run_validation_agent
from app.modules.planning.formatting_agent import run_formatting_agent
from app.core.progress_tracker import tracker

async def run_account_planning(filters: dict):
    tracker.emit("ag-orch", "started", message="Initiating Account Planning Mesh Lifecycle...")
    
    # 1. Data Agent
    raw_data = await run_data_agent(filters)
    accounts = [acc.account_id for acc in raw_data["accounts"].itertuples()][:5] # Limit to top 5 for demo
    
    # 2. Parallel Processing (Brief & Call Plan)
    tracker.emit("ag-orch", "processing", message="Delegating to Context and Strategy Agents...")
    briefs, call_plans = await asyncio.gather(
        run_brief_agent(accounts, raw_data),
        run_call_plan_agent(accounts, raw_data)
    )
    
    # 3. Validation
    # Adapt simple validation logic (brief existence check)
    validations = await run_validation_agent(briefs, raw_data)
    
    # 4. Formatting
    final_payload = await run_formatting_agent(briefs, call_plans, validations, raw_data)
    
    tracker.emit("ag-orch", "completed", message="Account Planning Lifecycle Complete. Returning payload.")
    return final_payload
