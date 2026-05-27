from app.core.progress_tracker import tracker
from app.core.llm_client import explain_llm_error, format_chain_failure, run_planning_chain

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


def _offline_call_plan_markdown(
    acc_id: str, contacts_str: str, gap_names_csv: str
) -> str:
    gaps = gap_names_csv or "identified product whitespace"
    people = contacts_str or "key stakeholders"
    return f"""### Tactical Call Plan

**Discovery questions**
1. What are your top investment-admin priorities for the next 12 months, and where do you see friction today?
2. How do you currently evaluate new fund-services or product extensions with {people.split(",")[0].strip() or "your team"}?
3. What would need to be true for IQ-EQ to earn a deeper mandate on the themes in your brief?

**Call objectives**
1. Validate fit and urgency around: {gaps}.
2. Agree on a concrete next step (workshop, deep-dive, or executive alignment) with {people}.

*(Structured offline template for {acc_id} — use when the live model is unavailable.)*"""


async def process_call_plan(acc_id, brief_markdown, raw_data, i, total, trace_id=None):
    accounts_df = raw_data["accounts"]
    contacts_df = raw_data["contacts"]
    matrix_df = raw_data["account_product_matrix"]
    catalog_df = raw_data["product_catalog"]

    acc_row = accounts_df[accounts_df.account_id == acc_id]
    acc_name = str(acc_row.iloc[0]["account_name"]) if not acc_row.empty else str(acc_id)
    
    # 1. Fetch Contacts
    account_contacts = contacts_df[contacts_df.account_id == acc_id]
    contacts_str = ", ".join(
        [
            f"{c.get('name', c.get('full_name', ''))} ({c.get('role', '')})"
            for _, c in account_contacts.iterrows()
        ]
    )
    
    # 2. Fetch Gaps
    gaps = matrix_df[(matrix_df.account_id == acc_id) & (matrix_df.is_active == False)]
    gap_names = []
    for _, row in gaps.iterrows():
        pid = row["product_id"]
        cr = catalog_df[catalog_df.product_id == pid]
        if cr.empty:
            gap_names.append(str(pid))
        else:
            gap_names.append(str(cr.iloc[0].get("product_name", pid)))
    
    # Progress Tracking Update (High Visibility)
    tracker.emit("ag-call", "processing", message=f"Crafting Tactical Call Plan for {acc_name} ({i+1}/{total})...", trace_id=trace_id)
    
    try:
        res = await run_planning_chain(PLAN_PROMPT, {
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
        err_code, user_msg = explain_llm_error(e)
        detail = format_chain_failure(e)
        return {
            "account_id": acc_id,
            "call_plan_markdown": _offline_call_plan_markdown(
                acc_id, contacts_str, ", ".join(gap_names)
            )
            + (
                f"\n\n---\n**Model note:** Call plan drafting could not reach the model ({err_code}). "
                f"{user_msg} Technical: {detail[:400]}"
            ),
        }

async def run_call_plan_agent(briefs: list, raw_data: dict, trace_id: str = None):
    tracker.emit("ag-call", "started", message=f"Initializing tactical question generation for {len(briefs)} prioritized targets...", trace_id=trace_id)
    
    results = []
    for i, b in enumerate(briefs):
        acc_id = b["account_id"]
        brief_md = b["brief_markdown"]
        res = await process_call_plan(acc_id, brief_md, raw_data, i, len(briefs), trace_id=trace_id)
        results.append(res)
        
    tracker.emit("ag-call", "completed", message=f"Tactical planning lifecycle complete for {len(results)} accounts.", trace_id=trace_id)
    return results
