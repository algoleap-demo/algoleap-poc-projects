import json
import asyncio
from app.core.progress_tracker import tracker
from app.core.llm_client import run_standard_chain

PLAN_PROMPT = """You are the 'Call Plan Strategist' for IQ-EQ.
Your goal is to turn a strategic account brief into tactical discovery questions and objectives.

Context:
- Account ID: {account_id}
- Strategic Brief: {brief}
- Stakeholder List: {contacts}
- Product Gaps: {gaps}

Instructions:
1. Provide 3 high-impact discovery questions tailored to the Stakeholders listed.
2. Define 2 clear call objectives based on the Product Gaps.
3. Keep the formatting punchy and designed for a mobile-first RM experience.

Return strict JSON: {{"account_id": "...", "call_plan_markdown": "### Tactical Call Plan\\n\\n..."}}"""

async def process_call_plan(acc_id, brief_markdown, raw_data, i, total, trace_id=None):
    accounts_df = raw_data["accounts"]
    contacts_df = raw_data["contacts"]
    matrix_df = raw_data["account_product_matrix"]
    catalog_df = raw_data["product_catalog"]
    
    acc_name = accounts_df[accounts_df.account_id == acc_id].iloc[0]["account_name"]
    
    # 1. Fetch Contacts
    account_contacts = contacts_df[contacts_df.account_id == acc_id]
    contacts_str = ", ".join([f"{c['name']} ({c['role']})" for _, c in account_contacts.iterrows()])
    
    # 2. Fetch Gaps
    gaps = matrix_df[(matrix_df.account_id == acc_id) & (matrix_df.is_active == False)]
    gap_names = []
    for _, row in gaps.iterrows():
        gap_names.append(catalog_df[catalog_df.product_id == row["product_id"]].iloc[0]["product_name"])
    
    # Progress Tracking Update (High Visibility)
    tracker.emit("ag-plan", "processing", message=f"Crafting Tactical Call Plan for {acc_name} ({i+1}/{total})...", trace_id=trace_id)
    
    try:
        res = await run_standard_chain(PLAN_PROMPT, {
            "account_id": acc_id,
            "brief": brief_markdown[:1000], # Substantial snippet of the brief
            "contacts": contacts_str or "Key Decision Makers",
            "gaps": ", ".join(gap_names)
        })
        
        return {
            "account_id": acc_id,
            "call_plan_markdown": res.get("call_plan_markdown", "### Plan Unavailable")
        }
    except Exception as e:
        return {
            "account_id": acc_id,
            "call_plan_markdown": f"### Error\n\nFailed to craft tactical plan: {str(e)}"
        }

async def run_call_plan_agent(briefs: list, raw_data: dict, trace_id: str = None):
    tracker.emit("ag-plan", "started", message=f"Initializing tactical question generation for {len(briefs)} prioritized targets...", trace_id=trace_id)
    
    results = []
    for i, b in enumerate(briefs):
        acc_id = b["account_id"]
        brief_md = b["brief_markdown"]
        res = await process_call_plan(acc_id, brief_md, raw_data, i, len(briefs), trace_id=trace_id)
        results.append(res)
        
    tracker.emit("ag-plan", "completed", message=f"Tactical planning lifecycle complete for {len(results)} accounts.", trace_id=trace_id)
    return results
