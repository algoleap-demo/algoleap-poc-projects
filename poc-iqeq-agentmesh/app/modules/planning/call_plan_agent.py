import json
import asyncio
from app.core.progress_tracker import tracker
from app.core.features import compute_features
from app.core.llm_client import run_standard_chain

CALL_PLAN_PROMPT = """You are the 'Strategic Planning Agent' for IQ-EQ.
Based on account signals, generate a 3-step call agenda and specific objectives.

Input Signals:
- Segment: {segment}
- Country: {country}
- Last Fund Launch: {launch}
- Major Conference Presence: {tier_1_count}

Instructions:
1. Define 2 primary 'Objectives'. Each must have a 'rationale'.
2. Define a 3-step 'Agenda'. Each step must have a 'topic' and a 'key_question'.
3. The agenda must be tailored to the segment and country (e.g., region focus).

Return strict JSON: 
{{
  "account_id": "...",
  "objectives": [
    {{"objective": "...", "rationale": "..."}}
  ],
  "agenda": [
    {{"step": 1, "topic": "...", "key_question": "..."}}
  ]
}}"""

async def process_call_plan(acc_id, raw_data, i, total):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]
    feat = compute_features(acc_id, raw_data)
    
    prompt = CALL_PLAN_PROMPT.format(
        segment=acc_info["segment"],
        country=acc_info["country"],
        launch="New Fund Detected" if feat["launch_indicator"] else "Steady State",
        tier_1_count=feat["tier_1_conf_count"]
    )
    
    tracker.emit("ag-callplan", "processing", message=f"Strategizing Call for {acc_id} ({i+1}/{total})...")
    
    try:
        res = await run_standard_chain(CALL_PLAN_PROMPT, {
            "segment": acc_info["segment"],
            "country": acc_info["country"],
            "launch": "New Fund Detected" if feat["launch_indicator"] else "Steady State",
            "tier_1_count": feat["tier_1_conf_count"]
        })
        return {
            "account_id": acc_id,
            "objectives": res.get("objectives", []),
            "agenda": res.get("agenda", [])
        }
    except Exception as e:
        return {
            "account_id": acc_id,
            "objectives": [],
            "agenda": []
        }

async def run_call_plan_agent(accounts: list, raw_data: dict):
    tracker.emit("ag-callplan", "started", message="Developing strategic objectives and meeting agenda...")
    
    results = []
    for i, acc_id in enumerate(accounts):
        res = await process_call_plan(acc_id, raw_data, i, len(accounts))
        results.append(res)
        
    tracker.emit("ag-callplan", "completed", message=f"Strategic Call Plans finalized for {len(results)} accounts.")
    return results
