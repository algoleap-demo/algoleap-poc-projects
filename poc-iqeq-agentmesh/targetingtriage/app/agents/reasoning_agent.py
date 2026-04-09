import json
import asyncio
from app.progress_tracker import tracker
from app.features import compute_features
from app.llm_client import call_router

# Prompt Template
REASONING_PROMPT = """You are the Reasoning Agent for IQ-EQ FAM/PIAO account triage.

Given an account with:
- propensity_score: {ml_score} (0-1, from XGBoost)
- confidence_level: {confidence}
- launch_indicator: {launch}
- tier_1_conf_count: {tier_1_count}
- segment: {segment}, country: {country}

Assign a priority bucket (A, B, or C) and write a one-sentence rationale.

Rules:
- Bucket A: strong commercial signal AND contextual catalyst (high ML score + high context)
- Bucket B: moderate signal OR mixed context (medium ML score or some context)
- Bucket C: weak signal AND no contextual catalyst (low ML score + low context)
- Rationale must reference at least one specific signal.

Return strict JSON: {{"priority_bucket": "A|B|C", "rationale_text": "..."}}"""

async def process_account_reasoning(acc_id, s_res, raw_data, i, total):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]
    feat = compute_features(acc_id, raw_data)
    
    prompt = REASONING_PROMPT.format(
        ml_score=s_res["propensity_score"],
        confidence=s_res["confidence_level"],
        launch=feat["launch_indicator"],
        tier_1_count=feat["tier_1_conf_count"],
        segment=acc_info["segment"],
        country=acc_info["country"]
    )
    
    tracker.emit("ag-reason", "processing", message=f"Reasoning for {acc_id} ({i+1}/{total})...")
    
    try:
        res = await call_router(prompt)
        return {
            "account_id": acc_id,
            "priority_bucket": res.get("priority_bucket", "B"),
            "rationale_text": res.get("rationale_text", "Processing complete.")
        }
    except Exception as e:
        # Fallback in case of LLM failure
        return {
            "account_id": acc_id,
            "priority_bucket": "B",
            "rationale_text": f"Contextual reasoning fallback due to connection error."
        }

async def run_reasoning_agent(scoring_results: list, raw_data: dict):
    tracker.emit("ag-reason", "started", message="Generating contextual rationales via OpenRouter...")
    
    results = []
    batch_size = 5 # Process 5 accounts at a time
    
    for i in range(0, len(scoring_results), batch_size):
        batch = scoring_results[i : i + batch_size]
        tasks = []
        for j, s_res in enumerate(batch):
            tasks.append(process_account_reasoning(s_res["account_id"], s_res, raw_data, i + j, len(scoring_results)))
        
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
    tracker.emit("ag-reason", "completed", message=f"Contextual reasoning finalized for {len(results)} accounts.")
    return results
