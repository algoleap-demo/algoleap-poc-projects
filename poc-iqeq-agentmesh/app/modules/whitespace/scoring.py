"""Deterministic whitespace scoring (POC3 §05)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from app.core.constants import COUNTRIES
from app.core.features_poc2 import matrix_has_product, matrix_potential_bucket
from app.modules.whitespace.constants import (
    EXPANSION_WEIGHT,
    WS_SCORE_WEIGHTS,
    EXPECTED_REVENUE_MAP,
)


def _strategic_flag(account_row: pd.Series) -> float:
    v = account_row.get("strategic_priority_flag")
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return 1.0 if float(v) else 0.0
    s = str(v).lower()
    return 1.0 if s in ("true", "1", "yes") else 0.0


def _expansion_weight(catalog: pd.DataFrame, product_id: str) -> float:
    row = catalog[catalog.product_id == product_id]
    if row.empty:
        return EXPANSION_WEIGHT["Medium"]
    key = str(row.iloc[0].get("expansion_potential", "Medium")).strip()
    return float(EXPANSION_WEIGHT.get(key, EXPANSION_WEIGHT["Medium"]))


def compute_ws_cell(
    account_row: pd.Series,
    product_row: pd.Series,
    cell_row: pd.Series,
) -> Dict[str, Any]:
    if matrix_has_product(cell_row):
        return {"whitespace_flag": 0, "expected_revenue_eur": 0, "ws_score": 0.0}

    bucket = matrix_potential_bucket(cell_row)
    if bucket not in ("Medium", "High"):
        return {"whitespace_flag": 0, "expected_revenue_eur": 0, "ws_score": 0.0}

    expected_rev = float(EXPECTED_REVENUE_MAP[bucket])
    normalized_rev = expected_rev / 300_000.0

    exp_key = str(product_row.get("expansion_potential", "Medium")).strip()
    exp_w = float(EXPANSION_WEIGHT.get(exp_key, EXPANSION_WEIGHT["Medium"]))
    strat = _strategic_flag(account_row)

    ws_score = (
        WS_SCORE_WEIGHTS["revenue"] * normalized_rev
        + WS_SCORE_WEIGHTS["expansion"] * exp_w
        + WS_SCORE_WEIGHTS["strategic"] * strat
    )
    return {
        "whitespace_flag": 1,
        "expected_revenue_eur": expected_rev,
        "ws_score": round(min(1.0, max(0.0, ws_score)), 4),
    }


def run_whitespace_scoring(raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    accounts_df = raw_data["accounts"]
    matrix_df = raw_data["account_product_matrix"]
    catalog_df = raw_data["product_catalog"].copy()
    product_ids: List[str] = sorted(catalog_df["product_id"].astype(str).unique().tolist())
    pid_to_idx = {p: i for i, p in enumerate(product_ids)}

    scored_cells: List[Dict[str, Any]] = []
    country_product_totals: Dict[Tuple[str, str], float] = {}

    for _, cell in matrix_df.iterrows():
        aid = str(cell["account_id"])
        pid = str(cell["product_id"])
        acc_match = accounts_df[accounts_df.account_id == aid]
        if acc_match.empty:
            continue
        account_row = acc_match.iloc[0]
        cat_match = catalog_df[catalog_df.product_id == pid]
        if cat_match.empty:
            continue
        product_row = cat_match.iloc[0]

        score = compute_ws_cell(account_row, product_row, cell)
        country = str(account_row.get("country", ""))
        segment = str(account_row.get("segment", ""))

        entry = {
            "account_id": aid,
            "product_id": pid,
            "product_line": str(product_row.get("product_line", product_row.get("product_name", ""))),
            "country": country,
            "segment": segment,
            **score,
        }
        scored_cells.append(entry)

        if score["whitespace_flag"] == 1:
            k = (country, pid)
            country_product_totals[k] = country_product_totals.get(k, 0.0) + float(
                score["expected_revenue_eur"]
            )

    by_account: Dict[str, Dict[str, Any]] = {}
    for aid in accounts_df["account_id"].astype(str).unique():
        by_account[str(aid)] = {
            "account_id": str(aid),
            "total_ws_potential_eur": 0.0,
            "ws_cell_count": 0,
            "vector": [0.0] * len(product_ids),
            "cell_scores_by_product": {},
        }

    for e in scored_cells:
        if e["whitespace_flag"] != 1:
            continue
        aid = e["account_id"]
        pid = e["product_id"]
        if aid not in by_account:
            continue
        ac = by_account[aid]
        ac["total_ws_potential_eur"] += float(e["expected_revenue_eur"])
        ac["ws_cell_count"] += 1
        idx = pid_to_idx[pid]
        ac["vector"][idx] = max(ac["vector"][idx], float(e["ws_score"]))
        ac["cell_scores_by_product"][pid] = e

    totals = [ac["total_ws_potential_eur"] for ac in by_account.values()]
    mx = max(totals) if totals else 0.0
    for aid, ac in by_account.items():
        ac["ws_intensity"] = (
            float(ac["total_ws_potential_eur"] / mx) if mx > 0 else 0.0
        )

    return {
        "scored_cells": scored_cells,
        "by_account": by_account,
        "country_product_totals": country_product_totals,
        "product_ids": product_ids,
        "countries_axis": list(COUNTRIES),
    }
