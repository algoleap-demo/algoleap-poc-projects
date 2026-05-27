"""Campaign Brief Agent — OpenRouter LLM, top-3 clusters only (POC3 §03.4, §06.2)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.features_poc2 import relationship_depth
from app.core.llm_client import explain_llm_error, format_chain_failure, run_poc3_campaign_chain
from app.core.progress_tracker import tracker

CAMPAIGN_BRIEF_PROMPT = """You are the Campaign Brief Agent for IQ-EQ FAM/PIAO whitespace analysis.

Given the following cluster:
- cluster_id: {cluster_id}
- member_accounts: {account_id_list} (count: {n})
- dominant_products: {top_2_products_by_ws_score}
- cluster_total_potential_eur: {total}
- dominant_country: {country}
- dominant_segment: {segment}
- representative account profile: avg_fund_size_eur={avg_fund_size_eur}, relationship_depth={relationship_depth}

Produce a campaign brief with exactly these sections:
1. messaging_angle (one sentence — the hook that unites this cluster)
2. objectives (3 bullets)
3. suggested_sequence (4 bullets — outreach sequence)
4. primary_cta (one short call-to-action)

Constraints:
- Do NOT invent account IDs. Only reference the provided member_accounts if needed.
- Do NOT invent product names outside dominant_products.
- Focus on commercial rationale, not technical product details.
- Total brief under 300 words.

Return strict JSON: {{
  "messaging_angle": "...",
  "campaign_brief_text": "...",
  "primary_cta": "..."
}}"""


def _dominant_products_for_cluster(
    cluster_id: int,
    cluster_members: Dict[int, List[str]],
    by_account: Dict[str, Dict[str, Any]],
    catalog_df: pd.DataFrame,
) -> List[str]:
    member_set = set(cluster_members.get(cluster_id, []))
    score_by_product: Dict[str, float] = {}
    for aid in member_set:
        ac = by_account.get(aid)
        if not ac:
            continue
        for pid, cell in ac.get("cell_scores_by_product", {}).items():
            if cell.get("whitespace_flag") != 1:
                continue
            w = float(cell.get("ws_score", 0)) * float(cell.get("expected_revenue_eur", 0))
            score_by_product[pid] = score_by_product.get(pid, 0.0) + w
    ranked_pids = sorted(score_by_product.keys(), key=lambda p: -score_by_product[p])
    names: List[str] = []
    for pid in ranked_pids[:2]:
        row = catalog_df[catalog_df.product_id == pid]
        if row.empty:
            names.append(pid)
        else:
            pl = row.iloc[0].get("product_line", row.iloc[0].get("product_name", pid))
            names.append(str(pl))
    return names if names else ["Whitespace opportunity"]


async def run_campaign_brief_agent(
    raw_data: Dict[str, pd.DataFrame],
    clustering_result: Dict[str, Any],
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    tracker.emit(
        "ag-camp",
        "START",
        message="Generating campaign briefs for top whitespace clusters (OpenRouter)...",
        trace_id=trace_id,
        agent_type="LLM",
        stage="DECISION",
    )

    by_account = clustering_result["by_account"]
    cluster_members: Dict[int, List[str]] = clustering_result["cluster_members"]
    top_cluster_ids: List[int] = clustering_result["top_cluster_ids"]
    catalog_df = raw_data["product_catalog"]
    accounts_df = raw_data["accounts"]

    briefs: List[Dict[str, Any]] = []

    for rank, cluster_id in enumerate(top_cluster_ids):
        members = cluster_members.get(cluster_id, [])
        if not members:
            continue

        total_pot = sum(
            float(by_account[a]["total_ws_potential_eur"]) for a in members if a in by_account
        )
        countries = []
        segments = []
        fund_sizes = []
        rel_depths = []
        for aid in members:
            row = accounts_df[accounts_df.account_id == aid]
            if row.empty:
                continue
            r = row.iloc[0]
            countries.append(str(r.get("country", "")))
            segments.append(str(r.get("segment", "")))
            fund_sizes.append(float(r.get("fund_size_eur", 0) or 0))
            rel_depths.append(relationship_depth(aid, raw_data))

        dom_country = Counter(countries).most_common(1)[0][0] if countries else ""
        dom_segment = Counter(segments).most_common(1)[0][0] if segments else ""
        avg_fund = sum(fund_sizes) / len(fund_sizes) if fund_sizes else 0.0
        avg_rel = sum(rel_depths) / len(rel_depths) if rel_depths else 0.0

        dom_products = _dominant_products_for_cluster(
            cluster_id, cluster_members, by_account, catalog_df
        )

        tracker.emit(
            "ag-camp",
            "processing",
            message=f"Campaign brief LLM call {rank + 1}/{len(top_cluster_ids)} (cluster {cluster_id})...",
            trace_id=trace_id,
            agent_type="LLM",
            stage="DECISION",
        )

        payload = {
            "cluster_id": cluster_id,
            "account_id_list": ", ".join(members[:25])
            + ("..." if len(members) > 25 else ""),
            "n": len(members),
            "top_2_products_by_ws_score": ", ".join(dom_products),
            "total": int(total_pot),
            "country": dom_country,
            "segment": dom_segment,
            "avg_fund_size_eur": f"{avg_fund:,.0f}",
            "relationship_depth": f"{avg_rel:.2f}",
        }
        try:
            llm_out = await run_poc3_campaign_chain(CAMPAIGN_BRIEF_PROMPT, payload)
        except Exception as e:
            code, user_msg = explain_llm_error(e)
            tech = format_chain_failure(e)[:280]
            tracker.emit(
                "ag-camp",
                "processing",
                message=(
                    f"Campaign brief LLM failed for cluster {cluster_id} ({code}: {user_msg}); "
                    f"using structured fallback."
                ),
                trace_id=trace_id,
                agent_type="LLM",
                stage="DECISION",
            )
            llm_out = {
                "messaging_angle": (
                    f"Prioritize whitespace in {dom_country or 'target markets'} "
                    f"for {dom_segment or 'this segment'} — €{int(total_pot):,} indicated cluster potential."
                ),
                "campaign_brief_text": (
                    f"Cluster {cluster_id} ({len(members)} accounts): lead with dominant lines "
                    f"{', '.join(dom_products)}. Sequence: (1) executive hook on growth/admin burden, "
                    f"(2) quantify upside using cluster totals, (3) propose a working session to rank plays, "
                    f"(4) secure owners and a dated follow-up. "
                    f"(Offline brief — {code}: {user_msg} Technical: {tech})"
                ),
                "primary_cta": "Book a 45-minute whitespace prioritization session with the account team.",
            }

        briefs.append(
            {
                "cluster_id": cluster_id,
                "target_account_count": len(members),
                "cluster_total_potential_eur": total_pot,
                "dominant_country": dom_country,
                "dominant_segment": dom_segment,
                "dominant_products": dom_products,
                "messaging_angle": str(llm_out.get("messaging_angle", "")),
                "campaign_brief_text": str(llm_out.get("campaign_brief_text", "")),
                "primary_cta": str(llm_out.get("primary_cta", "")),
            }
        )

    tracker.emit(
        "ag-camp",
        "END",
        message=f"Completed {len(briefs)} campaign brief(s).",
        trace_id=trace_id,
        agent_type="LLM",
        stage="OUTPUT",
    )
    return briefs
