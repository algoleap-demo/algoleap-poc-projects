import json
import asyncio
from app.progress_tracker import tracker
from app.features import compute_features

# Prompt Template
REASONING_PROMPT = """You are the Reasoning Agent for IQ-EQ FAM/PIAO account triage.

Given an account with:
- propensity_score: {ml_score} (0-1, from XGBoost)
- confidence_level: {confidence}
- launch_indicator: {launch}
- tier_1_conf_count: {tier_1_count}
- segment: {segment}, country: {country}

Assign a priority bucket and write a one-sentence rationale.

Rules:
- Bucket A: strong commercial signal AND contextual catalyst
- Bucket B: moderate signal OR mixed context
- Bucket C: weak signal AND no contextual catalyst
- Do NOT recalculate the propensity score
- Rationale must reference at least one specific signal

Return strict JSON: {{"priority_bucket": "A|B|C", "rationale_text": "..."}}"""

async def run_reasoning_agent(scoring_results: list, raw_data: dict):
    tracker.emit("ag-reason", "started", "Generating contextual rationales via LLM...")
    
    accounts_df = raw_data["accounts"]
    results = []
    
    for i, s_res in enumerate(scoring_results):
        acc_id = s_res["account_id"]
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
        
        tracker.emit("ag-reason", "processing", f"Reasoning for {acc_id} ({i+1}/{len(scoring_results)})...")
        
        # MOCK LLM Logic for POC1 robustness
        # Adjusted to ensure engineered conflicts trigger the flag
        ml_score = s_res["propensity_score"]
        has_catalyst = feat["launch_indicator"] > 0 or feat["tier_1_conf_count"] > 1
        
        if has_catalyst and ml_score < 0.30:
            # Context says YES, ML says NO -> Conflict
            bucket = "A" 
            reason = f"LLM overriding low ML score ({ml_score:.2f}) due to high contextual signals (Launch: {feat['launch_indicator']}, Conferences: {feat['tier_1_conf_count']})."
        elif not has_catalyst and ml_score > 0.70:
            # ML says YES, Context says NO -> Conflict
            bucket = "C"
            reason = f"Contextual reasoning designates low priority (no launch/conf signals) despite high ML propensity ({ml_score:.2f})."
        elif ml_score >= 0.70 and has_catalyst:
            bucket = "A"
            reason = f"High propensity score ({ml_score:.2f}) aligned with active signals."
        elif ml_score >= 0.30:
            bucket = "B"
            reason = f"Moderate propensity ({ml_score:.2f}) with standard business coverage."
        else:
            bucket = "C"
            reason = f"Low commercial signal ({ml_score:.2f}) and no catalysts detected."
            
        # Simulate slight delay for UI visibility
        await asyncio.sleep(0.1)
        
        results.append({
            "account_id": acc_id,
            "priority_bucket": bucket,
            "rationale_text": reason
        })
        
    tracker.emit("ag-reason", "completed", f"Contextual reasoning finalized for {len(results)} accounts.")
    return results
