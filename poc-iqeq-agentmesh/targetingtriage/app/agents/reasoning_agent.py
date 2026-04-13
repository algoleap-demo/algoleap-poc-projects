import json
import asyncio
from typing import List
from app.progress_tracker import tracker
from app.features import compute_features
from app.llm_client import get_model, LLM_SEMAPHORE, is_free_tier
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Prompt Template
REASONING_PROMPT = ChatPromptTemplate.from_template("""
You are the Reasoning Agent for IQ-EQ FAM/PIAO account triage.

Given an account with:
- propensity_score: {ml_score} (0-1, from XGBoost)
- confidence_level: {confidence}
- revenue_concentration: {rev_conc}
- launch_indicator: {launch}
- tier_1_conf_count: {tier_1_count}
- segment: {segment}, country: {country}

Assign a priority bucket (A, B, or C), suggest a Next Best Action (NBA), and write a rationale structured by these weights:
1. Historical Weight (60%): Mention Win Rate or Deal Size signals.
2. Firmographic Fit (80%): Mention Revenue Concentration, Segment or Country catalysts.
3. Timing Signal (100%): Mention specific fund launches or conference attendance.

Rules:
- NBA Rules: action_type: ["call", "email", "meeting", "send_link", "schedule"], description, reasoning, due_in_days (A: 1-5, B: 7-21, C: 30-90).
- Return strict json: {{"priority_bucket": "A|B|C", "rationale_text": "...", "suggested_nba": {{"action_type": "...", "description": "...", "reasoning": "...", "due_in_days": 1}}}}
""")

async def process_account_reasoning(acc_id, s_res, raw_data, i, total):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]
    feat = compute_features(acc_id, raw_data)
    
    tracker.emit("ag-reason", "processing", message=f"Reasoning for {acc_id} ({i+1}/{total})...")
    
    model = get_model(json_mode=True)
    parser = JsonOutputParser()
    chain = REASONING_PROMPT | model | parser
    
    try:
        async with LLM_SEMAPHORE:
            res = await chain.ainvoke({
                "ml_score": s_res["propensity_score"],
                "confidence": s_res["confidence_level"],
                "rev_conc": feat["revenue_concentration"],
                "launch": feat["launch_indicator"],
                "tier_1_count": feat["tier_1_conf_count"],
                "segment": acc_info["segment"],
                "country": acc_info["country"]
            })
        
        # Strict validation of LLM output
        if "priority_bucket" not in res:
            raise ValueError(f"LLM response missing 'priority_bucket' for {acc_id}")
        if "suggested_nba" not in res or "reasoning" not in res["suggested_nba"]:
            raise ValueError(f"LLM response missing 'suggested_nba.reasoning' for {acc_id}")

        return {
            "account_id": acc_id,
            "priority_bucket": res["priority_bucket"],
            "rationale_text": res.get("rationale_text", "Reasoning generated successfully."),
            "suggested_nba": res["suggested_nba"]
        }
    except Exception as e:
        print(f"Error in Reasoning Node for {acc_id}: {e}")
        # Re-raise to let the graph handle the failure
        raise

async def run_reasoning_agent(scoring_results: list, raw_data: dict):
    is_free = is_free_tier()
    if is_free:
        tracker.emit("ag-reason", "info", message="Free Tier Active: Optimizing Reasoning for Top 20 high-priority accounts.")
        scoring_results = scoring_results[:20]

    tracker.emit("ag-reason", "started", message="Generating contextual rationales via LangChain Graph...")
    
    results = []
    batch_size = 5 # Process 5 accounts at a time
    
    for i in range(0, len(scoring_results), batch_size):
        batch = scoring_results[i : i + batch_size]
        tasks = []
        for j, s_res in enumerate(batch):
            tasks.append(process_account_reasoning(s_res["account_id"], s_res, raw_data, i + j, len(scoring_results)))
        
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        if is_free and (i + batch_size) < len(scoring_results):
            # Play nice with free tier rate limits
            await asyncio.sleep(1.5)
            
    tracker.emit("ag-reason", "completed", message=f"Contextual reasoning finalized for {len(results)} accounts.")
    return results
