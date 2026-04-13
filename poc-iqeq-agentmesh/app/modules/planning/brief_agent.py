"""
POC2 Account Brief Agent — single LLM call per account (brief + call plan), OpenRouter only.
"""
import json
from typing import Dict, List

from app.core.progress_tracker import tracker
from app.core.llm_client import run_planning_chain

ACCOUNT_BRIEF_PROMPT = """You are the Account Brief Agent for IQ-EQ FAM/PIAO account planning.

Given the following structured account data:
- account_id: {account_id}
- country: {country}
- segment: {segment}
- fund_size_eur: {fund_size_eur}
- propensity_score (0-1, from XGBoost): {propensity_score}
- confidence_level (0-1): {confidence_level}
- total_ws_potential_eur: {total_ws_potential_eur}
- relationship_depth (0-1): {relationship_depth}
- api_score (0-1): {api_score}
- top 3 whitespace opportunities (JSON): {top_whitespace_json}
- top 3 contacts by influence (JSON): {top_contacts_json}

Produce a structured 1-page account brief with exactly 5 sections:
1. Summary (2-3 sentences, lead with api_score interpretation)
2. Relationship & Performance (reference relationship_depth and engagement context)
3. Whitespace & Upsell Opportunities (reference top 3 by expected_rev_eur)
4. Key Contacts (reference top 3 by influence_score)
5. Recommended Next Actions (3 bullet points, aligned with api_score: high ≥0.75 prioritize QBR; mid0.5–0.75 discovery; low <0.5 nurture)

Also produce a call_plan_text for the highest-influence contact with:
- Objectives (3 bullets)
- Suggested agenda (4 bullets)
- Key questions (3 bullets)

Constraints:
- Do NOT invent numbers. Every statistic must come from the structured input above.
- Do NOT recalculate propensity, whitespace totals, or api_score.
- Do NOT recommend actions outside the API bands described (QBR / discovery / nurture).

Return strict JSON: {{"brief_text": "...", "call_plan_text": "..."}}"""


def _coerce_llm_text(val) -> str:
    """LLM JSON may use strings or nested objects for brief/call_plan fields."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False, indent=2).strip()
    return str(val).strip()


async def process_brief(
    acc_id: str,
    raw_data: dict,
    score_row: Dict,
    i: int,
    total: int,
    trace_id=None,
):
    accounts_df = raw_data["accounts"]
    acc_info = accounts_df[accounts_df.account_id == acc_id].iloc[0]

    tracker.emit(
        "ag-brief",
        "processing",
        message=f"Synthesizing account brief for {acc_id} ({i + 1}/{total})...",
        trace_id=trace_id,
    )

    top_ws = score_row.get("whitespace_summary") or []
    top_ct = score_row.get("top_contacts") or []

    try:
        res = await run_planning_chain(
            ACCOUNT_BRIEF_PROMPT,
            {
                "account_id": acc_id,
                "country": str(acc_info.get("country", "")),
                "segment": str(acc_info.get("segment", "")),
                "fund_size_eur": float(acc_info.get("fund_size_eur", 0) or 0),
                "propensity_score": round(float(score_row["propensity_score"]), 4),
                "confidence_level": round(float(score_row["confidence_level"]), 4),
                "total_ws_potential_eur": float(score_row["total_ws_potential_eur"]),
                "relationship_depth": round(float(score_row["relationship_depth"]), 4),
                "api_score": round(float(score_row["api_score"]), 4),
                "top_whitespace_json": json.dumps(top_ws, ensure_ascii=False),
                "top_contacts_json": json.dumps(top_ct, ensure_ascii=False),
            },
        )
        brief = _coerce_llm_text(res.get("brief_text")) or _coerce_llm_text(
            res.get("brief_markdown")
        )
        cplan = _coerce_llm_text(res.get("call_plan_text")) or _coerce_llm_text(
            res.get("call_plan_markdown")
        )
        return {
            "account_id": acc_id,
            "brief_text": brief,
            "call_plan_text": cplan,
            "brief_markdown": brief,
            "call_plan_markdown": cplan,
        }
    except Exception as e:
        err = f"Error generating brief: {str(e)}"
        return {
            "account_id": acc_id,
            "brief_text": err,
            "call_plan_text": err,
            "brief_markdown": err,
            "call_plan_markdown": err,
        }


async def run_brief_agent(
    accounts: List[str],
    raw_data: dict,
    scoring_rows: List[Dict],
    trace_id: str = None,
):
    tracker.emit(
        "ag-brief",
        "started",
        message=f"Account Brief Agent (single LLM pass per account) for {len(accounts)} target(s)...",
        trace_id=trace_id,
    )
    by_id = {r["account_id"]: r for r in scoring_rows}
    results = []
    for i, acc_id in enumerate(accounts):
        row = by_id.get(acc_id, {})
        res = await process_brief(acc_id, raw_data, row, i, len(accounts), trace_id)
        results.append(res)

    tracker.emit(
        "ag-brief",
        "completed",
        message=f"Account briefs complete for {len(results)} account(s).",
        trace_id=trace_id,
    )
    return results
