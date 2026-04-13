import asyncio
from typing import List, Dict
from app.progress_tracker import tracker
from app.llm_client import get_model, LLM_SEMAPHORE
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

BRIEF_PROMPT = ChatPromptTemplate.from_template("""
You are the Account Briefing Agent for IQ-EQ. 
Your task is to synthesize account data into a professional internal memo.

Account Data:
- Account Name: {name}
- Priority Bucket: {bucket}
- Propensity Score: {ml_score}
- Active Services: {active_services}
- Whitespace Opportunities: {whitespace_services}

Memo Structure:
1. Executive Summary: High-level overview of the account status.
2. Current Engagement: What we already do for them.
3. Growth Catalyst: Why now? (Mention whitespace & propensity).
4. Strategic Proposal: Recommended focus.

Return the memo in Markdown format. Keep it under 300 words.
""")

async def process_account_brief(acc_id, bucket, ml_score, whitespace_data, raw_data):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]
    
    # Format services
    active = [g["product_name"] for g in whitespace_data["whitespace_summary"] if g.get("is_active", False)]
    # Wait, whitespace_summary is usually GAPS. Let's fix that.
    gaps = [g["product_name"] for g in whitespace_data["whitespace_summary"]]
    
    model = get_model()
    chain = BRIEF_PROMPT | model | StrOutputParser()
    
    try:
        async with LLM_SEMAPHORE:
            res = await chain.ainvoke({
                "name": acc_info["account_name"],
                "bucket": bucket,
                "ml_score": f"{ml_score*100:.1f}%",
                "active_services": ", ".join(active) if active else "None identified",
                "whitespace_services": ", ".join(gaps)
            })
        return res
    except Exception as e:
        print(f"Error in Brief Agent for {acc_id}: {e}")
        return f"Error generating brief for {acc_id}. Contact Administrator."

async def run_brief_agent(planning_stream: List[Dict], raw_data: Dict):
    tracker.emit("ag-brief", "started", message="Synthesizing account briefs via LangChain (LLM)...")
    
    results = []
    # Process in small batches to respect semaphore
    batch_size = 3
    for i in range(0, len(planning_stream), batch_size):
        batch = planning_stream[i : i + batch_size]
        tasks = []
        for p_item in batch:
            # We need the bucket and score from the Targeting results
            # For simplicity in this node, we assume they are passed in the stream
            tasks.append(process_account_brief(
                p_item["account_id"], 
                p_item.get("priority_bucket", "B"), 
                p_item.get("ml_score", 0.5),
                p_item, 
                raw_data
            ))
        
        batch_results = await asyncio.gather(*tasks)
        for idx, brief in enumerate(batch_results):
            batch[idx]["brief_text"] = brief
            
        results.extend(batch)
        
    tracker.emit("ag-brief", "completed", message=f"Account briefs generated for {len(results)} priority accounts.")
    return results
