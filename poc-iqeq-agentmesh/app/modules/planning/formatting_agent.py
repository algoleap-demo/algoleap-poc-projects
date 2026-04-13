"""Assemble POC2 §08 JSON and validate with Pydantic."""
from datetime import datetime
from typing import List
import uuid

from app.core.constants import MODEL_VERSION_POC2
from app.core.progress_tracker import tracker
from app.core.schemas import POC2AccountOutput, POC2PipelineResponse, WhitespaceSummaryItem


def _resolve_nba(api_score: float) -> List[dict]:
    if api_score >= 0.75:
        return [
            {
                "action_type": "qbr",
                "description": "Schedule Quarterly Business Review",
                "due_in_days": 7,
                "reasoning": "api_score ≥ 0.75",
            }
        ]
    if api_score >= 0.5:
        return [
            {
                "action_type": "brief_plus_call",
                "description": "Send tailored brief + book discovery call",
                "due_in_days": 14,
                "reasoning": "0.5 ≤ api_score < 0.75",
            }
        ]
    return [
        {
            "action_type": "nurture",
            "description": "Add to quarterly nurture campaign",
            "due_in_days": 90,
            "reasoning": "api_score < 0.5",
        }
    ]


def _ws_summary_items(scoring_row: dict) -> List[WhitespaceSummaryItem]:
    raw = scoring_row.get("whitespace_summary") or []
    out = []
    for cell in raw[:3]:
        product = str(cell.get("product", cell.get("product_line", "")))
        ev = float(cell.get("expected_rev_eur", 0))
        out.append(WhitespaceSummaryItem(product=product, expected_rev_eur=ev))
    return out


async def run_formatting_agent(
    briefs: list,
    validations: list,
    scoring_rows: list,
    raw_data: dict = None,
    trace_id: str = None,
):
    tracker.emit(
        "ag-fmt",
        "started",
        message="Building POC2 planning payload (Pydantic §08)...",
        trace_id=trace_id,
    )
    score_by_id = {r["account_id"]: r for r in scoring_rows}
    valid_by_id = {v["account_id"]: v for v in validations}
    accounts_df = raw_data["accounts"] if raw_data is not None else None
    accounts_out: List[POC2AccountOutput] = []

    for b in briefs:
        acc_id = b["account_id"]
        sc = score_by_id.get(acc_id, {})
        v = valid_by_id.get(acc_id, {})

        brief_text = b.get("brief_text") or b.get("brief_markdown", "")
        call_plan_text = b.get("call_plan_text") or b.get("call_plan_markdown", "")
        api = max(0.0, min(1.0, float(sc.get("api_score", 0.0))))
        rel_d = max(0.0, min(1.0, float(sc.get("relationship_depth", 0.0))))

        row = {
            "account_id": acc_id,
            "api_score": api,
            "propensity_score": max(0.0, min(1.0, float(sc.get("propensity_score", 0.0)))),
            "confidence_level": max(0.0, min(1.0, float(sc.get("confidence_level", 0.0)))),
            "total_ws_potential_eur": float(sc.get("total_ws_potential_eur", 0.0)),
            "relationship_depth": rel_d,
            "brief_text": brief_text,
            "call_plan_text": call_plan_text,
            "whitespace_summary": [s.model_dump() for s in _ws_summary_items(sc)],
            "nba_actions": _resolve_nba(api),
            "conflict_flag": bool(v.get("conflict_flag", False)),
            "review_notes": str(v.get("review_notes", "") or ""),
        }
        accounts_out.append(POC2AccountOutput.model_validate(row))

    payload = POC2PipelineResponse(
        pipeline_run_id=trace_id or str(uuid.uuid4()),
        generated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_version=MODEL_VERSION_POC2,
        accounts=accounts_out,
    )
    data = payload.model_dump()

    results = []
    for acc in data["accounts"]:
        d = dict(acc)
        d["brief_markdown"] = d["brief_text"]
        d["call_plan_markdown"] = d["call_plan_text"]
        if accounts_df is not None:
            m = accounts_df[accounts_df.account_id == acc["account_id"]]
            if not m.empty:
                d["account_name"] = str(m.iloc[0].get("account_name", acc["account_id"]))
                d["contact_person"] = str(m.iloc[0].get("contact_person", ""))
            else:
                d["account_name"] = acc["account_id"]
                d["contact_person"] = ""
        else:
            d["account_name"] = acc["account_id"]
            d["contact_person"] = ""
        d["conflict_flag"] = acc["conflict_flag"]
        results.append(d)

    data["results"] = results

    tracker.emit(
        "ag-fmt",
        "completed",
        message=f"Payload validated for {len(accounts_out)} account(s).",
        trace_id=trace_id,
    )
    return data


def validate_poc2_payload_or_raise(obj: dict) -> POC2PipelineResponse:
    """For tests: strict re-validation."""
    return POC2PipelineResponse.model_validate(obj)
