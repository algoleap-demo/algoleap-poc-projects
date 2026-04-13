# IQ-EQ Unified Agent Mesh — Context (Repo Root)

This file is the **integration map** for the authoritative implementation under `app/`, `data/raw/`, and `models/`. Older copies under `targetingtriage/` and `accountplanning/` may lag; treat this file plus [`plan.md`](plan.md) as the source of truth for **what ships**.

**Stakeholder / architecture deep-dive:** [`ARCHITECTURE.md`](ARCHITECTURE.md) — flow diagrams (Mermaid), formulas, LLM routing, algorithms.  
**Operations & handover:** [`HANDOVER.md`](HANDOVER.md) — `.env`, runbook, troubleshooting.

---

## Current status (2026)

All three POCs run in one FastAPI app with shared telemetry (`/events` SSE), audit logging, and a **unified dashboard** at `/` (`app/static/index.html`).

| POC | Role | Module / entry |
|-----|------|----------------|
| **POC 1** | Targeting & Triage — XGBoost propensity + reasoning LLM + validation + formatting | `app/modules/targeting/` · `run_targeting_pipeline` / `run_pipeline` |
| **POC 2** | Account Planning — data + whitespace/API scoring + **OpenRouter** brief + **OpenRouter** call plan + validation + formatting | `app/modules/planning/` · `run_account_planning` |
| **POC 3** | Whitespace — matrix scoring + k-means + **OpenRouter** campaign briefs (top clusters) + validation + formatting + CSV | `app/modules/whitespace/` · `run_whitespace_pipeline` |

---

## Technical stack

- **API:** FastAPI, Uvicorn; dashboard `GET /` serves `app/static/index.html`.
- **Orchestration:** LangGraph `StateGraph` in [`app/main.py`](app/main.py): `targeting → planning → whitespace` for **full mission** (`POST /execute_mission`); stepwise runs via `POST /run/poc1`, `/run/poc2`, `/run/poc3`.
- **Progress:** [`app/core/progress_tracker.py`](app/core/progress_tracker.py) — SSE for live agent logs.
- **LLM:** LangChain chat models; **POC2** brief + call plan and **POC3** campaigns use **OpenRouter** (`OPENROUTER_API_KEY`, `POC2_LLM_MODEL`, `POC3_LLM_MODEL`). **POC1** reasoning follows provider order in [`app/core/llm_client.py`](app/core/llm_client.py) (`get_model()`).
- **ML:** XGBoost classifier `predict_proba` — artifact `models/xgb_propensity_v1.pkl`, features `FEATURE_ORDER` in [`app/core/constants.py`](app/core/constants.py).
- **Clustering (POC3):** scikit-learn **KMeans** — `KMEANS_K=5`, `random_state=42` ([`app/modules/whitespace/constants.py`](app/modules/whitespace/constants.py)).
- **Data:** [`data/raw/*.csv`](data/raw/) — shared backbone; POC3 uses enriched `product_catalog.csv` (expansion_potential, region_fit, etc.) where present.
- **Audit:** [`app/core/audit_logger.py`](app/core/audit_logger.py) — `logs/audit.jsonl`; POC3 validation flags may append to `logs/governance_queue.jsonl` via `log_poc3_governance_flag`.

---

## Dashboard

- **Layout:** ~50/50 — mesh SVG [`app/static/mesh_architecture.svg`](app/static/mesh_architecture.svg) + agent logs / mission output.
- **Tabs:** Targeting & Triage · Account Planning · Whitespace — labels drive output column titles; tab click runs the next pending phase when applicable.
- **Mesh node IDs** align with `tracker.emit` names: `ag-data`, `ag-ml`, `ag-ws`, `ag-brief`, `ag-reason`, `ag-call`, `ag-camp`, `ag-valid`, `ag-fmt`, `ag-orch`. UI may map aliases (e.g. `ag-plan` → `ag-call`).
- **Results API:** `GET /mission_results` returns last `targeting`, `planning`, `whitespace` payloads from `mission_store`.

---

## Deeper references

- **Architecture (formulas, diagrams, LLM table):** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Handover / runbook:** [`HANDOVER.md`](HANDOVER.md)
- **Completed plan / backlog:** [`plan.md`](plan.md)
- POC3 module notes: [`whitespace/context.md`](whitespace/context.md), [`whitespace/plan.md`](whitespace/plan.md)
- Legacy narrative: [`targetingtriage/context.md`](targetingtriage/context.md)

---

## Out of scope (prototype)

Production CRM/Snowflake, full Copilot shell, governance workbench UI beyond JSONL append, auth/RBAC — see `ARCHITECTURE.md` §8 for stakeholder wording.
