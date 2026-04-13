"""POC2 Validation Agent — §06.1 conflict rules + governance queue."""
from typing import Dict, List

from app.core.audit_logger import log_governance_conflict
from app.core.constants import (
    CONFLICT_HIGH_PROPENSITY_WS_MAX,
    CONFLICT_LOW_PROPENSITY_WS_MIN,
)
from app.core.progress_tracker import tracker


def _is_conflict(propensity: float, ws_potential_eur: float) -> tuple:
    if propensity >= 0.7 and ws_potential_eur < CONFLICT_HIGH_PROPENSITY_WS_MAX:
        return (
            True,
            "High propensity but negligible whitespace — already saturated account",
        )
    if propensity <= 0.3 and ws_potential_eur > CONFLICT_LOW_PROPENSITY_WS_MIN:
        return (
            True,
            "Large whitespace but low buying intent — review targeting strategy",
        )
    return False, ""


def run_validation_agent(
    briefs: List[dict],
    scoring_by_account: Dict[str, dict],
    trace_id: str = None,
) -> List[dict]:
    tracker.emit(
        "ag-valid",
        "started",
        message="POC2 consistency validation (propensity vs whitespace)...",
        trace_id=trace_id,
    )
    results = []
    for b in briefs:
        acc_id = b["account_id"]
        sc = scoring_by_account.get(acc_id, {})
        prop = float(sc.get("propensity_score", 0.5))
        ws = float(sc.get("total_ws_potential_eur", 0.0))
        flag, notes = _is_conflict(prop, ws)

        if flag and trace_id:
            log_governance_conflict(
                trace_id,
                acc_id,
                "propensity_whitespace_mismatch",
                notes,
            )

        results.append(
            {
                "account_id": acc_id,
                "conflict_flag": flag,
                "review_notes": notes,
            }
        )

    tracker.emit(
        "ag-valid",
        "completed",
        message=f"Validation complete for {len(results)} account(s).",
        trace_id=trace_id,
    )
    return results
