# IQ-EQ Agent Mesh: POC3 Whitespace — Context & Standards

## Current status

POC3 is **production-ready in the unified repo** under [`app/modules/whitespace/`](../app/modules/whitespace/). It is reachable as:

- `POST /analyze_whitespace` — standalone run (full outer `ag-orch` + all agents).
- `POST /run/poc3` — stepwise run (stores result in `mission_store`; emits completion on `ag-orch`).
- `POST /execute_mission` — embedded via `run_whitespace_pipeline(..., embed_parent=True)` (no duplicate outer orchestrator bookends).

Runtime data: [`data/raw/`](../data/raw/) (same backbone as POC1/POC2). Demo uses **six** products (`P-FA` … `P-CORP`); vectors and heatmap dimensions follow the catalog.

## Mission

Identify gaps from the account–product matrix, rank whitespace with deterministic **`ws_score`**, cluster accounts with **k-means** (`k=5`, `random_state=42`, `n_init=10`), generate **three cluster-level campaign briefs** via **OpenRouter** (sequential LLM calls), run **validation** (§06.1), and return JSON (heatmap, top accounts, briefs, flags) plus **`outputs/whitespace_top50_<run_id>.csv`**.

## Technical stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2.
- **Scoring**: [`scoring.py`](../app/modules/whitespace/scoring.py) — POC3 §05 formulas; [`constants.py`](../app/modules/whitespace/constants.py) for weights and thresholds.
- **Clustering**: [`clustering.py`](../app/modules/whitespace/clustering.py) — scikit-learn `KMeans`.
- **LLM**: [`get_poc3_campaign_model` / `run_poc3_campaign_chain`](../app/core/llm_client.py) — LangChain `ChatOpenAI` → OpenRouter (`POC3_LLM_MODEL`).
- **Orchestration**: [`whitespace_orchestrator.py`](../app/modules/whitespace/whitespace_orchestrator.py) — strict sequential `await` chain; optional `console=True` for CLI prints.
- **Audit**: `logs/audit.jsonl` via `log_audit`; POC3 validation flags via `log_poc3_governance_flag` → `logs/governance_queue.jsonl`.

## Telemetry IDs (dashboard / SSE)

These **`agent_name` values** match the unified mesh SVG (`ag-camp` = Campaign Agent; **not** `ag-brief`, which is reserved for POC2 Account Brief):

| Stage | `tracker.emit` id |
|--------|-------------------|
| Data | `ag-data` |
| Scoring + k-means | `ag-ml` |
| Campaign briefs (LLM) | `ag-camp` |
| Validation | `ag-valid` |
| Formatting | `ag-fmt` |
| Standalone pipeline shell | `ag-orch` (skipped when `embed_parent=True`) |

## Agent pipeline (linear)

1. **Data agent** — load POC1 tables + `contacts` + matrix + catalog; optional filters; FK checks.
2. **Scoring + clustering** — per-cell scores, rollups, country×product totals, k-means, top-3 clusters by potential.
3. **Campaign brief agent** — three sequential OpenRouter JSON calls (locked prompt §06.2).
4. **Validation agent** — rules + XGBoost propensity from [`models/xgb_propensity_v1.pkl`](../models/xgb_propensity_v1.pkl).
5. **Formatting agent** — Pydantic §08 payload, normalized heatmap, top accounts, CSV (50 rows, pad if needed).

## Alignment with POC1/2

- Same **`ProgressTracker`** SSE pattern as targeting/planning.
- Shared **repo-root dashboard** at `/` loads [`mesh_architecture.svg`](../app/static/mesh_architecture.svg) and maps log `agent_name` to SVG groups (including `ag-camp`).

## Out of scope (prototype)

Copilot UI, live CRM/Snowflake, interactive heatmap rendering, per-account NBA (POC2), dynamic k, IQEQ.AI tenant (Phase 2).

## Requirements source

[`whitespace/requirements/POC3_Requirements_v3.md`](requirements/POC3_Requirements_v3.md).
