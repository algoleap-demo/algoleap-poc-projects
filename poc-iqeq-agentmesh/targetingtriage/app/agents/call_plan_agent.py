import asyncio
from typing import List, Dict
from app.progress_tracker import tracker
from app.llm_client import get_model, LLM_SEMAPHORE
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

CALL_PLAN_PROMPT = ChatPromptTemplate.from_template("""
You are the Tactical Sales Advisor for IQ-EQ. 
Based on the provided Account Brief and Whitespace analysis, generate a tactical call plan.

Account Brief:
{brief}

Whitespace Potential:
{whitespace_details}

Objectives:
- Provide 3 tailored discovery questions to uncover needs for missing services.
- Provide 2 specific cross-sell objectives for this call.
- Anticipate 1 common objection and provide a rebuttal.

Keep it punchy and actionable for a senior sales executive.
""")

async def process_call_plan(acc_id, brief, whitespace_data):
    # Format whitespace details for prompt
    gaps = [f"- {g['product_name']}" for g in whitespace_data["whitespace_summary"]]
    ws_text = "\n".join(gaps) if gaps else "No major gaps identified."
    
    model = get_model()
    chain = CALL_PLAN_PROMPT | model | StrOutputParser()
    
    try:
        async with LLM_SEMAPHORE:
            res = await chain.ainvoke({
                "brief": brief,
                "whitespace_details": ws_text
            })
        return res
    except Exception as e:
        print(f"Error in Call Plan Agent for {acc_id}: {e}")
        return "Tactical call plan unavailable due to system error."

async def run_call_plan_agent(planning_stream: List[Dict]):
    tracker.emit("ag-plan", "started", message="Generating tactical call plans via LangChain (LLM)...")
    
    results = []
    batch_size = 3
    for i in range(0, len(planning_stream), batch_size):
        batch = planning_stream[i : i + batch_size]
        tasks = []
        for p_item in batch:
            tasks.append(process_call_plan(
                p_item["account_id"], 
                p_item.get("brief_text", ""), 
                p_item
            ))
        
        batch_results = await asyncio.gather(*tasks)
        for idx, plan in enumerate(batch_results):
            batch[idx]["call_plan_text"] = plan
            
        results.extend(batch)
        
    tracker.emit("ag-plan", "completed", message=f"Tactical call plans finalized for {len(results)} accounts.")
    return results
