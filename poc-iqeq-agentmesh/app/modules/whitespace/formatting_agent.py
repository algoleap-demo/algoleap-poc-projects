"""Assemble POC3 response, heatmap, CSV export (POC3 §03.6, §08)."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.paths import OUTPUTS_DIR
from app.core.progress_tracker import tracker
from app.modules.whitespace.constants import MODEL_VERSION_POC3
from app.modules.whitespace.schemas import (
    CampaignBriefItem,
    TopAccountItem,
    ValidationFlagItem,
    WhitespaceAnalysisResponse,
    WhitespaceGridSchema,
)


def _normalize_matrix(values: List[List[float]]) -> List[List[float]]:
    flat = [v for row in values for v in row]
    if not flat:
        return values
    lo, hi = min(flat), max(flat)
    if hi <= lo:
        return [[0.5 for _ in row] for row in values]
    return [
        [round((v - lo) / (hi - lo), 4) for v in row] for row in values
    ]


def run_formatting_agent(
    pipeline_run_id: str,
    raw_data: Dict[str, pd.DataFrame],
    clustering_result: Dict[str, Any],
    campaign_briefs: List[Dict[str, Any]],
    validation_flags: List[Dict[str, Any]],
    trace_id: Optional[str] = None,
) -> WhitespaceAnalysisResponse:
    tracker.emit(
        "ag-fmt",
        "START",
        message="Assembling whitespace grid, top accounts, and CSV export...",
        trace_id=trace_id,
        agent_type="API",
        stage="ACTION",
    )

    scored_cells: List[Dict[str, Any]] = clustering_result["scored_cells"]
    by_account: Dict[str, Dict[str, Any]] = clustering_result["by_account"]
    country_product_totals: Dict[Any, float] = clustering_result["country_product_totals"]
    product_ids: List[str] = clustering_result["product_ids"]
    countries_axis: List[str] = clustering_result["countries_axis"]

    grid_raw: List[List[float]] = []
    for country in countries_axis:
        row = []
        for pid in product_ids:
            row.append(float(country_product_totals.get((country, pid), 0.0)))
        grid_raw.append(row)

    intensity_matrix = _normalize_matrix(grid_raw)

    total_potential = sum(
        float(ac["total_ws_potential_eur"])
        for ac in by_account.values()
 )

    ranked_accounts = sorted(
        by_account.values(),
        key=lambda x: -float(x["total_ws_potential_eur"]),
    )
    top_accounts: List[TopAccountItem] = []
    for ac in ranked_accounts[:50]:
        aid = ac["account_id"]
        by_ws = sorted(
            ac.get("cell_scores_by_product", {}).values(),
            key=lambda c: -float(c.get("ws_score", 0)),
        )
        top_pids = [str(c["product_id"]) for c in by_ws[:3]]
        top_accounts.append(
            TopAccountItem(
                account_id=aid,
                total_ws_potential_eur=float(ac["total_ws_potential_eur"]),
                ws_intensity=float(ac.get("ws_intensity", 0)),
                top_products=top_pids,
                cluster_id=int(ac.get("cluster_id", -1)),
            )
        )

    brief_items = [
        CampaignBriefItem(
            cluster_id=int(b["cluster_id"]),
            target_account_count=int(b["target_account_count"]),
            cluster_total_potential_eur=float(b["cluster_total_potential_eur"]),
            dominant_country=str(b["dominant_country"]),
            dominant_segment=str(b.get("dominant_segment", "")),
            dominant_products=list(b["dominant_products"]),
            messaging_angle=str(b["messaging_angle"]),
            campaign_brief_text=str(b["campaign_brief_text"]),
            primary_cta=str(b["primary_cta"]),
        )
        for b in campaign_briefs
    ]

    flag_items = [
        ValidationFlagItem(
            account_id=str(f["account_id"]),
            product_id=str(f["product_id"]),
            flag_type=f["flag_type"],
            anomaly_note=str(f["anomaly_note"]),
        )
        for f in validation_flags
    ]

    ws_cells = [c for c in scored_cells if c.get("whitespace_flag") == 1]
    ws_cells.sort(key=lambda c: -float(c.get("ws_score", 0)))
    export_rows = list(ws_cells[:50])
    pad_template = {
        "account_id": "N/A",
        "product_id": "N/A",
        "product_line": "",
        "country": "",
        "expected_revenue_eur": 0,
        "ws_score": 0.0,
        "cluster_id": -1,
        "_pad": True,
    }
    while len(export_rows) < 50:
        export_rows.append(dict(pad_template))

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    csv_name = f"whitespace_top50_{pipeline_run_id}.csv"
    csv_path = OUTPUTS_DIR / csv_name
    catalog_df = raw_data["product_catalog"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "account_id",
                "product_id",
                "product_line",
                "country",
                "expected_rev_eur",
                "ws_score",
                "cluster_id",
            ]
        )
        for row in export_rows[:50]:
            if row.get("_pad"):
                w.writerow(["N/A", "N/A", "", "", 0, 0.0, -1])
                continue
            aid = row["account_id"]
            pid = row["product_id"]
            pl = row.get("product_line", "")
            if not pl:
                cr = catalog_df[catalog_df.product_id == pid]
                if not cr.empty:
                    pl = str(cr.iloc[0].get("product_line", cr.iloc[0].get("product_name", "")))
            cid = int(by_account.get(aid, {}).get("cluster_id", -1))
            w.writerow(
                [
                    aid,
                    pid,
                    pl,
                    row.get("country", ""),
                    int(row.get("expected_revenue_eur", 0)),
                    float(row.get("ws_score", 0)),
                    cid,
                ]
            )

    response = WhitespaceAnalysisResponse(
        pipeline_run_id=pipeline_run_id,
        generated_at=datetime.now(timezone.utc),
        model_version=MODEL_VERSION_POC3,
        total_potential_eur=float(total_potential),
        whitespace_grid=WhitespaceGridSchema(
            countries=countries_axis,
            products=product_ids,
            intensity_matrix=intensity_matrix,
        ),
        top_accounts=top_accounts,
        campaign_briefs=brief_items,
        validation_flags=flag_items,
        export_csv_path=f"outputs/{csv_name}",
    )

    tracker.emit(
        "ag-fmt",
        "END",
        message=f"Formatting complete. CSV: {csv_name}",
        trace_id=trace_id,
        agent_type="API",
        stage="OUTPUT",
    )
    return response
