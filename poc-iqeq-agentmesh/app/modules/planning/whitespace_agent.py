"""
POC2 Whitespace + propensity scoring (deterministic except XGBoost inference).
Implements §03.3 / §05 with fallbacks when optional CSV columns are absent.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from typing import Dict, List

from app.core.constants import EXPECTED_REVENUE_MAP, FEATURE_ORDER, MODEL_VERSION_POC2
from app.core.features import compute_features
from app.core.features_poc2 import (
    compute_api_score,
    matrix_has_product,
    normalize_ws_potentials,
    relationship_depth,
    top_contacts_for_account,
    whitespace_flag,
)
from app.core.paths import MODELS_DIR
from app.core.progress_tracker import tracker


def _propensity_for_accounts(
    raw_data: Dict[str, pd.DataFrame], account_ids: List[str]
) -> Dict[str, tuple]:
    """Returns account_id -> (propensity_score, confidence_level)."""
    model_path = MODELS_DIR / "xgb_propensity_v1.pkl"
    if not model_path.exists():
        tracker.emit(
            "ag-ml",
            "warning",
            message=f"Model missing at {model_path}; using neutral propensity 0.5.",
        )
        return {a: (0.5, 0.55) for a in account_ids}

    model_data = joblib.load(model_path)
    clf = model_data["model"]

    X_list = []
    for acc_id in account_ids:
        feat_dict = compute_features(acc_id, raw_data)
        X_list.append([feat_dict[f] for f in FEATURE_ORDER])
    X = np.array(X_list)
    probs = clf.predict_proba(X)[:, 1]

    out = {}
    for i, acc_id in enumerate(account_ids):
        raw_prob = float(probs[i])
        confidence = min(0.98, (abs(raw_prob - 0.5) / 0.5) * 0.4 + 0.55)
        out[acc_id] = (raw_prob, confidence)
    return out


def run_whitespace_agent(
    raw_data: Dict[str, pd.DataFrame], accounts: List[str], trace_id: str = None
) -> List[Dict]:
    tracker.emit(
        "ag-ml",
        "started",
        message=f"POC2: XGBoost propensity for {len(accounts)} account(s)...",
        trace_id=trace_id,
    )

    matrix_df = raw_data["account_product_matrix"]
    catalog_df = raw_data["product_catalog"]

    prop_by_acc = _propensity_for_accounts(raw_data, accounts)
    tracker.emit(
        "ag-ml",
        "completed",
        message="POC2: propensity inference complete.",
        trace_id=trace_id,
    )

    tracker.emit(
        "ag-ws",
        "started",
        message=f"POC2: whitespace matrix scoring for {len(accounts)} account(s)...",
        trace_id=trace_id,
    )
    ws_totals: Dict[str, float] = {}
    details: Dict[str, List[Dict]] = {a: [] for a in accounts}

    for acc_id in accounts:
        acc_matrix = matrix_df[matrix_df.account_id == acc_id]
        total_ws = 0.0
        for _, row in acc_matrix.iterrows():
            if not whitespace_flag(row):
                continue
            bucket = (
                str(row["potential_revenue_bucket"]).strip()
                if "potential_revenue_bucket" in row.index
                and pd.notna(row.get("potential_revenue_bucket"))
                else "Medium"
            )
            if bucket not in EXPECTED_REVENUE_MAP:
                bucket = "Medium"
            ev = float(EXPECTED_REVENUE_MAP[bucket])
            total_ws += ev
            prod_id = str(row["product_id"])
            cat = catalog_df[catalog_df.product_id == prod_id]
            product_line = (
                str(cat.iloc[0].get("product_line", cat.iloc[0].get("product_name", "")))
                if not cat.empty
                else prod_id
            )
            details[acc_id].append(
                {
                    "product": product_line,
                    "product_id": prod_id,
                    "expected_rev_eur": ev,
                    "potential_revenue_bucket": bucket,
                }
            )
        ws_totals[acc_id] = total_ws

    norm_ws = normalize_ws_potentials(ws_totals)
    accounts_df = raw_data["accounts"]
    results = []

    for i, acc_id in enumerate(accounts):
        tracker.emit(
            "ag-ws",
            "processing",
            message=f"Scoring account {acc_id} ({i + 1}/{len(accounts)})...",
            trace_id=trace_id,
        )
        row = accounts_df[accounts_df.account_id == acc_id].iloc[0]
        strategic = bool(row.get("strategic_priority_flag", False))
        prop, conf = prop_by_acc[acc_id]
        nws = norm_ws.get(acc_id, 0.0)
        api = compute_api_score(prop, nws, strategic)
        rel_depth = relationship_depth(acc_id, raw_data)
        top_ws = sorted(
            details[acc_id], key=lambda x: -x["expected_rev_eur"]
        )[:3]
        top_people = top_contacts_for_account(acc_id, raw_data, k=3)

        results.append(
            {
                "account_id": acc_id,
                "propensity_score": prop,
                "confidence_level": conf,
                "total_ws_potential_eur": ws_totals[acc_id],
                "relationship_depth": rel_depth,
                "api_score": api,
                "whitespace_summary": top_ws,
                "top_contacts": top_people,
                "model_version": MODEL_VERSION_POC2,
            }
        )

    tracker.emit(
        "ag-ws",
        "completed",
        message=f"POC2: whitespace scoring complete for {len(results)} account(s).",
        trace_id=trace_id,
    )
    return results
