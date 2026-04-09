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

Assign a priority bucket (A, B, or C), write a one-sentence rationale, and suggest the Next Best Action (NBA).

NBA Rules:
- action_type: one of ["call", "email", "meeting", "send_link", "schedule"]
- description: concise action summary (e.g., "Schedule Q3 Strategy Review")
- reasoning: why this specific action for this specific client signal?
- due_in_days: integer (priority A: 1-5, B: 7-21, C: 30-90)

Return strict JSON: 
{{
  "priority_bucket": "A|B|C", 
  "rationale_text": "...",
  "suggested_nba": {{
    "action_type": "...",
    "description": "...",
    "reasoning": "...",
    "due_in_days": 10
  }}
}}"""

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
        default_nba = {
            "action_type": "email",
            "description": "Follow up on automated scoring",
            "reasoning": "Standard follow-up based on propensity signals.",
            "due_in_days": 7
        }
        return {
            "account_id": acc_id,
            "priority_bucket": res.get("priority_bucket", "B"),
            "rationale_text": res.get("rationale_text", "Processing complete."),
            "suggested_nba": res.get("suggested_nba", default_nba)
        }
    except Exception as e:
        # Fallback in case of LLM failure
        return {
            "account_id": acc_id,
            "priority_bucket": "B",
            "rationale_text": f"Contextual reasoning fallback due to connection error.",
            "suggested_nba": {
                "action_type": "email",
                "description": "Manual review required",
                "reasoning": "LLM connection error during dynamic NBA synthesis.",
                "due_in_days": 1
            }
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
