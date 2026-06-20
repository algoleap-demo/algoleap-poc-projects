# POC 3 Technical Specification — Whitespace Analysis (v4.0)

## 01 Executive Summary
This specification defines the whitespace clustering and campaign generation pipeline, leveraging the hardened **LangGraph** core. POC 3 introduces **k-means clustering** into the agentic mesh.

## 02 Architectural Alignment (POC 1 Hardening)
- **Node Resilience**: All nodes use `@retry(stop=stop_after_attempt(3))` and the shared `llm_client.py`.
- **Concurrency**: Campaign brief generation is throttled via `LLM_SEMAPHORE`.
- **State Registry**: Shared state `WhitespaceState` captures full cluster metadata and telemetry.

## 03 Agent definitions (Hardened)

### 03.1 Whitespace Scoring Agent
- **K-Means Clustering**: Performs deterministic clustering (k=5) on the product gap vector.
- **Rollup**: Computes `ws_intensity` at the country and segment level.

### 03.2 Campaign Brief Agent (LLM)
- **Hardening**: Limits concurrent brief generation (max 3 at a time).
- **Output**: Returns JSON messaging angles and CTAs per cluster.

### 03.3 Validation Agent
- **Logic**: Conflict detection for "Region Mismatch" and "Propensity-to-Whitespace gaps".

## 04 Output Metadata
- **Heatmap Matrix**: Deterministic country x product intensity matrix.
- **CSV Export**: Hardened export to `outputs/whitespace_top50_{run_id}.csv` with audit trail.

---

## 05 Shared Resources
- **Model**: Symlink to POC 1's `xgb_propensity_v1.pkl`.
- **Data**: Shared access to `account_product_matrix.csv` (POC 2).
