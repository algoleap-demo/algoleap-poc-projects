"""Sequential POC3 pipeline: Data → Scoring+Clusters → Campaign LLM → Validation → Formatting."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.audit_logger import log_audit
from app.core.pipeline_timing import AGENT_HANDOFF_DELAY_SEC
from app.core.progress_tracker import tracker
from app.modules.whitespace.campaign_brief_agent import run_campaign_brief_agent
from app.modules.whitespace.clustering import run_clustering
from app.modules.whitespace.data_agent import run_whitespace_data_agent
from app.modules.whitespace.formatting_agent import run_formatting_agent
from app.modules.whitespace.schemas import WhitespaceAnalysisResponse
from app.modules.whitespace.scoring import run_whitespace_scoring
from app.modules.whitespace.validation_agent import run_whitespace_validation_agent


def _console(console: bool, agent_name: str, status: str, message: str) -> None:
    if console:
        print(f"[{agent_name}] {status}: {message}", flush=True)


async def run_whitespace_pipeline(
    trace_id: Optional[str] = None,
    countries: Optional[List[str]] = None,
    segment: Optional[str] = None,
    product_ids: Optional[List[str]] = None,
    *,
    console: bool = False,
    embed_parent: bool = False,
) -> Dict[str, Any]:
    """If embed_parent=True, skip outer ag-orch START/END (used when POC3 runs inside unified LangGraph)."""
    pipeline_run_id = trace_id or str(uuid.uuid4())
    t_all = time.time()

    if not embed_parent:
        tracker.emit(
            "ag-orch",
            "START",
            message=f"POC3 Whitespace pipeline started. run_id={pipeline_run_id}",
            trace_id=pipeline_run_id,
            agent_type="RULE",
            stage="PLAN",
        )
        _console(console, "ag-orch", "START", f"POC3 Whitespace pipeline run_id={pipeline_run_id}")
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

    try:
        t0 = time.time()
        raw_data = run_whitespace_data_agent(
            trace_id=pipeline_run_id,
            countries=countries,
            segment=segment,
            product_ids=product_ids,
        )
        log_audit(pipeline_run_id, "whitespace_data_agent", time.time() - t0, None, {"tables": list(raw_data.keys())})
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        t0 = time.time()
        tracker.emit(
            "ag-ws",
            "START",
            message="POC3: computing whitespace scores and k-means clusters...",
            trace_id=pipeline_run_id,
            agent_type="RULE",
            stage="PLAN",
        )
        _console(console, "ag-ws", "START", "Whitespace scoring + clustering")

        scoring_result = run_whitespace_scoring(raw_data)
        clustered = run_clustering(scoring_result)

        tracker.emit(
            "ag-ws",
            "END",
            message="POC3: scoring and clustering complete.",
            trace_id=pipeline_run_id,
            agent_type="RULE",
            stage="OUTPUT",
        )
        _console(console, "ag-ws", "END", "Scoring and clustering complete")
        log_audit(
            pipeline_run_id,
            "whitespace_scoring_agent",
            time.time() - t0,
            {"accounts": len(raw_data["accounts"])},
            {"clusters": clustered.get("cluster_totals"), "top": clustered.get("top_cluster_ids")},
        )
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        t0 = time.time()
        campaign_briefs = await run_campaign_brief_agent(
            raw_data, clustered, trace_id=pipeline_run_id
        )
        log_audit(
            pipeline_run_id,
            "whitespace_campaign_brief_agent",
            time.time() - t0,
            {"clusters": clustered.get("top_cluster_ids")},
            campaign_briefs,
        )
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        t0 = time.time()
        validation_flags = run_whitespace_validation_agent(
            raw_data,
            clustered["scored_cells"],
            raw_data["product_catalog"],
            trace_id=pipeline_run_id,
        )
        log_audit(
            pipeline_run_id,
            "whitespace_validation_agent",
            time.time() - t0,
            {"cells": len(clustered["scored_cells"])},
            validation_flags,
        )
        await asyncio.sleep(AGENT_HANDOFF_DELAY_SEC)

        t0 = time.time()
        final = run_formatting_agent(
            pipeline_run_id,
            raw_data,
            clustered,
            campaign_briefs,
            validation_flags,
            trace_id=pipeline_run_id,
        )
        log_audit(
            pipeline_run_id,
            "whitespace_formatting_agent",
            time.time() - t0,
            {"flags": len(validation_flags)},
            final.model_dump(),
        )

        total_dur = time.time() - t_all
        if not embed_parent:
            tracker.emit(
                "ag-orch",
                "END",
                message=f"POC3 pipeline completed in {total_dur:.2f}s.",
                trace_id=pipeline_run_id,
                agent_type="RULE",
                stage="OUTPUT",
            )
            _console(console, "ag-orch", "END", f"Completed in {total_dur:.2f}s")
            log_audit(
                pipeline_run_id,
                "whitespace_orchestration",
                total_dur,
                {"phase": "complete"},
                {"export": final.export_csv_path},
            )

        return final.model_dump(mode="json")
    except Exception as e:
        tracker.emit(
            "ag-orch",
            "FAILED",
            message=str(e),
            trace_id=pipeline_run_id,
            agent_type="RULE",
            stage="ERROR",
        )
        _console(console, "ag-orch", "FAILED", str(e))
        raise
