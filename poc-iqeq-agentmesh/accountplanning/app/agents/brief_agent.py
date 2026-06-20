import json
import asyncio
from app.progress_tracker import tracker
from app.features import compute_features
from app.llm_client import call_router, is_free_tier

BRIEF_PROMPT = """You are the 'Briefing Agent' for IQ-EQ Relationship Managers.
Your goal is to synthesize account signals into a 1-page executive brief.

Input Signals:
- Propensity Score: {{ml_score}}
- Segment: {{segment}}
- Country: {{country}}
- Last Fund Launch: {{launch}}
- Major Conference Presence: {{tier_1_count}} tier-1 events

Instructions:
1. Write a section titled 'Account Snapshot'.
2. Write a section titled 'Key Catalysts' highlighting why we should act NOW.
3. Write a section titled 'Relationship Strategy' suggesting the best approach.
4. Keep the total length around 250 words.
5. Use professional, strategic language.

Return strict JSON: {{"account_id": "...", "brief_markdown": "### Account Brief\\n\\n..."}}"""

async def process_brief(acc_id, raw_data, i, total):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]
    feat = compute_features(acc_id, raw_data)
    
    # In a real POC2, we'd pass the ML score from earlier or recalculate. 
    # For standalone POC2 demo, we assume a high-propensity input.
    prompt = BRIEF_PROMPT.format(
        ml_score="0.85 (Predicted)",
        segment=acc_info["segment"],
        country=acc_info["country"],
        launch="New Fund Detected" if feat["launch_indicator"] else "Steady State",
        tier_1_count=feat["tier_1_conf_count"]
    )
    
    tracker.emit("ag-brief", "processing", message=f"Synthesizing Brief for {acc_id} ({i+1}/{total})...")
    
    try:
        res = await call_router(prompt)
        return {
            "account_id": acc_id,
            "brief_markdown": res.get("brief_markdown", "# Brief Unavailable")
        }
    except Exception as e:
        return {
            "account_id": acc_id,
            "brief_markdown": f"Error generating brief: {str(e)}"
        }

async def run_brief_agent(accounts: list, raw_data: dict):
    is_free = is_free_tier()
    if is_free:
        tracker.emit("ag-brief", "info", message="Free Tier Active: Optimizing Briefing for Top 15 high-priority accounts.")
        accounts = accounts[:15]

    tracker.emit("ag-brief", "started", message="Initiating contextual briefing synthesis...")
    
    results = []
    for i, acc_id in enumerate(accounts):
        res = await process_brief(acc_id, raw_data, i, len(accounts))
        results.append(res)
        
        if is_free and (i + 1) < len(accounts):
            # Briefs are heavy; play extra nice
            await asyncio.sleep(1.5)
            
    tracker.emit("ag-brief", "completed", message=f"Briefing packages finalized for {len(results)} accounts.")
    return results
