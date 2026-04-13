"""Load and validate POC1 + POC2 tables for POC3 (§04)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.paths import DATA_RAW
from app.core.progress_tracker import tracker


def run_whitespace_data_agent(
    trace_id: Optional[str] = None,
    countries: Optional[List[str]] = None,
    segment: Optional[str] = None,
    product_ids: Optional[List[str]] = None,
) -> Dict[str, pd.DataFrame]:
    tracker.emit(
        "ag-data",
        "START",
        message="Loading POC1/POC2 datasets for whitespace analysis...",
        trace_id=trace_id,
        agent_type="API",
        stage="PLAN",
    )

    tables = [
        "accounts",
        "opportunities",
        "snowflake_metrics",
        "external_funds",
        "conferences",
        "conference_attendance",
        "contacts",
        "account_product_matrix",
        "product_catalog",
    ]

    raw_data: Dict[str, pd.DataFrame] = {}
    for table in tables:
        path = DATA_RAW / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required data file: {path}")
        raw_data[table] = pd.read_csv(path)

    account_ids = set(raw_data["accounts"].account_id.astype(str))

    for table in [
        "opportunities",
        "snowflake_metrics",
        "external_funds",
        "conference_attendance",
        "contacts",
        "account_product_matrix",
    ]:
        col = raw_data[table]
        if "account_id" not in col.columns:
            continue
        orphans = col[~col.account_id.astype(str).isin(account_ids)]
        if not orphans.empty:
            raise ValueError(
                f"Data Integrity Error: {len(orphans)} orphaned records in {table}"
            )

    m = raw_data["account_product_matrix"]
    cat_ids = set(raw_data["product_catalog"].product_id.astype(str))
    bad_products = m[~m.product_id.astype(str).isin(cat_ids)]
    if not bad_products.empty:
        raise ValueError(
            f"account_product_matrix references unknown product_id ({len(bad_products)} rows)"
        )

    acc_df = raw_data["accounts"]
    if countries:
        acc_df = acc_df[acc_df.country.isin(countries)]
    if segment:
        acc_df = acc_df[acc_df.segment == segment]

    kept_ids = set(acc_df.account_id.astype(str))
    raw_data["accounts"] = acc_df.reset_index(drop=True)
    raw_data["account_product_matrix"] = m[
        m.account_id.astype(str).isin(kept_ids)
    ].reset_index(drop=True)

    if product_ids:
        pset = set(product_ids)
        raw_data["account_product_matrix"] = raw_data["account_product_matrix"][
            raw_data["account_product_matrix"].product_id.astype(str).isin(pset)
        ]
        raw_data["product_catalog"] = raw_data["product_catalog"][
            raw_data["product_catalog"].product_id.astype(str).isin(pset)
        ].reset_index(drop=True)

    for table in [
        "opportunities",
        "snowflake_metrics",
        "external_funds",
        "conference_attendance",
        "contacts",
    ]:
        raw_data[table] = raw_data[table][
            raw_data[table].account_id.astype(str).isin(kept_ids)
        ].reset_index(drop=True)

    tracker.emit(
        "ag-data",
        "END",
        message=f"Validated {len(raw_data['accounts'])} accounts for whitespace run.",
        trace_id=trace_id,
        agent_type="API",
        stage="OUTPUT",
    )
    return raw_data
