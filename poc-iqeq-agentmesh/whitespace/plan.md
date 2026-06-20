# Project Plan: POC3 Whitespace Analysis

Tracks milestones for the Whitespace mesh in the **unified** [`app/`](../app/) tree. For cross-POC status see repo-root [`plan.md`](../plan.md).

## Current status

**Complete** for rapid-prototype scope: deterministic scoring, clustering, OpenRouter campaign briefs, validation, CSV export, tests, and **integration into the unified dashboard and LangGraph full mission**.

## Completed milestones

### 1. Data & scoring
- [x] Enriched [`data/raw/product_catalog.csv`](../data/raw/product_catalog.csv) (`product_line`, `expansion_potential`, `region_fit`).
- [x] `potential_revenue_bucket` on [`account_product_matrix.csv`](../data/raw/account_product_matrix.csv) for golden-path (`ACME-EU-90001`) and region-mismatch demos.
- [x] [`scoring.py`](../app/modules/whitespace/scoring.py) — `compute_ws_cell`, rollups, heatmap inputs.
- [x] [`data_agent.py`](../app/modules/whitespace/data_agent.py) — includes `contacts`; filter + integrity checks.

### 2. Clustering & LLM
- [x] [`clustering.py`](../app/modules/whitespace/clustering.py) — `KMeans` k=5, seed42, `n_init=10`; top-3 clusters by total potential.
- [x] [`campaign_brief_agent.py`](../app/modules/whitespace/campaign_brief_agent.py) — OpenRouter, **`ag-camp`** telemetry, sequential calls.
- [x] [`llm_client.py`](../app/core/llm_client.py) — `POC3_LLM_MODEL`, `run_poc3_campaign_chain`.

### 3. Validation & outputs
- [x] [`validation_agent.py`](../app/modules/whitespace/validation_agent.py) — §06.1; `log_poc3_governance_flag`.
- [x] [`formatting_agent.py`](../app/modules/whitespace/formatting_agent.py) + [`schemas.py`](../app/modules/whitespace/schemas.py) — Pydantic response, `outputs/whitespace_top50_<run_id>.csv`.

### 4. Orchestration & embedding
- [x] [`whitespace_orchestrator.py`](../app/modules/whitespace/whitespace_orchestrator.py) — per-agent `log_audit`; `embed_parent` for LangGraph; scoring stage uses **`ag-ml`** (shared mesh node with POC1 ML box).
- [x] Removed obsolete [`whitespace/orchestration_agent.py`](orchestration_agent.py) skeleton (implementation lives under `app/modules/whitespace/`).

### 5. API & CLI
- [x] `POST /analyze_whitespace` on [`app/main.py`](../app/main.py).
- [x] `POST /run/poc3` for stepwise unified flow.
- [x] [`scripts/run_poc3.py`](../scripts/run_poc3.py) — `console=True` progress.

### 6. Tests & docs
- [x] [`tests/test_poc3_*.py`](../tests/) — bounds, k-means, golden path (mocked LLM), schema negative test.
- [x] [`whitespace/README.md`](README.md), [`context.md`](context.md), this file.
- [x] [`scripts/extract_mesh_svg.py`](../scripts/extract_mesh_svg.py) — regenerate [`app/static/mesh_architecture.svg`](../app/static/mesh_architecture.svg) from `IQ_EQ_Agent_Mesh_2.html`.

### 7. Unified dashboard
- [x] [`app/static/index.html`](../app/static/index.html) — POC3 tab, mission output (`renderWhitespace`),50/50 mesh + SSE logs.
- [x] Full mission LangGraph node `whitespace` after `planning`.

## Future (Phase 2+)

- [ ] Optional expansion to **eight** products for strict parity with legacy PROD-01…08 examples.
- [ ] Heatmap drill-down or export presets for sales ops.
- [ ] IQEQ.AI tenant swap (mirror POC2 in `llm_client.py`).
- [ ] Cross-mission analytics (run history) — out of prototype scope.
