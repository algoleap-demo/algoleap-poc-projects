"""Whitespace validation rules — deterministic (POC3 §03.5, §06.1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.core.audit_logger import log_poc3_governance_flag
from app.core.constants import FEATURE_ORDER
from app.core.features import compute_features
from app.core.paths import MODELS_DIR
from app.core.progress_tracker import tracker
from app.modules.whitespace.constants import WS_HIGH_THRESHOLD


def _propensity_by_account(raw_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    model_path = MODELS_DIR / "xgb_propensity_v1.pkl"
    accounts = raw_data["accounts"].account_id.astype(str).tolist()
    if not model_path.exists():
        return {a: 0.5 for a in accounts}
    model_data = joblib.load(model_path)
    clf = model_data["model"]
    X_list = []
    for acc_id in accounts:
        feat_dict = compute_features(acc_id, raw_data)
        X_list.append([feat_dict[f] for f in FEATURE_ORDER])
    X = np.array(X_list)
    probs = clf.predict_proba(X)[:, 1]
    return {accounts[i]: float(probs[i]) for i in range(len(accounts))}


def _region_countries(region_fit: str) -> List[str]:
    if not region_fit or not str(region_fit).strip():
        return []
    return [x.strip() for x in str(region_fit).split(",") if x.strip()]


def run_whitespace_validation_agent(
    raw_data: Dict[str, pd.DataFrame],
    scored_cells: List[Dict[str, Any]],
    catalog_df: pd.DataFrame,
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    tracker.emit(
        "ag-valid",
        "START",
        message="Running whitespace validation and governance checks...",
        trace_id=trace_id,
        agent_type="RULE",
        stage="PLAN",
    )

    propensity = _propensity_by_account(raw_data)
    cat_by_pid = {str(r.product_id): r for _, r in catalog_df.iterrows()}
    flags: List[Dict[str, Any]] = []

    for cell in scored_cells:
        aid = cell["account_id"]
        pid = cell["product_id"]
        if cell.get("whitespace_flag") != 1:
            continue

        ws = float(cell.get("ws_score", 0))
        prod_row = cat_by_pid.get(pid)
        if prod_row is None:
            continue

        exp_pot = str(prod_row.get("expansion_potential", "Medium")).strip()
        country = str(cell.get("country", ""))
        regions = _region_countries(str(prod_row.get("region_fit", "")))

        if ws >= WS_HIGH_THRESHOLD and exp_pot == "Low":
            note = "High ws_score on a Low expansion_potential product — review scoring weights"
            flags.append(
                {
                    "account_id": aid,
                    "product_id": pid,
                    "flag_type": "review",
                    "anomaly_note": note,
                }
            )
            log_poc3_governance_flag(trace_id or "", aid, pid, "review", note)

        if regions and country and country not in regions:
            note = f"Product {pid} region_fit does not include {country}"
            flags.append(
                {
                    "account_id": aid,
                    "product_id": pid,
                    "flag_type": "warning",
                    "anomaly_note": note,
                }
            )
            log_poc3_governance_flag(trace_id or "", aid, pid, "warning", note)

        ps = propensity.get(aid, 0.5)
        if ps <= 0.3 and ws >= WS_HIGH_THRESHOLD:
            note = "Large whitespace opportunity but low buying intent — review targeting"
            flags.append(
                {
                    "account_id": aid,
                    "product_id": pid,
                    "flag_type": "review",
                    "anomaly_note": note,
                }
            )
            log_poc3_governance_flag(trace_id or "", aid, pid, "review", note)

    tracker.emit(
        "ag-valid",
        "END",
        message=f"Validation complete ({len(flags)} flag(s)).",
        trace_id=trace_id,
        agent_type="RULE",
        stage="OUTPUT",
    )
    return flags
