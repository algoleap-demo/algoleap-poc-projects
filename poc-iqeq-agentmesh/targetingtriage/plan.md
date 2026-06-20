# Project Plan: IQ-EQ Agent Mesh Dashboard

This document tracks the milestones, completed work, and future roadmap for the Targeting & Triage Agent Mesh.

## Current Status: POC 1–3 live in repo-root `app/`
Targeting & Triage logic is implemented in [`app/modules/targeting/`](../app/modules/targeting/). The **unified** FastAPI app ([`app/main.py`](../app/main.py)) runs POC1 → POC2 → POC3 for a full mission and serves the **dashboard** ([`app/static/`](../app/static/)) with the architecture SVG derived from [`plan/IQ_EQ_Agent_Mesh_2.html`](plan/IQ_EQ_Agent_Mesh_2.html). This file tracks historical milestones for the `targetingtriage/` folder; **roll-up status**: see repo-root [`plan.md`](../plan.md).


## Completed Milestones

### 1. Backend Core (Phase 1)
- [x] Defined 6-agent linear pipeline (Orchestrator → Data → ML → Reason → Valid → Fmt).
- [x] Implemented standard Pydantic schemas for inter-agent communication.
- [x] Integrated `agentic-ai-blueprint` router for LLM reasoning.
- [x] Built `Validation Agent` for conflict detection (ML vs LLM scoring).

### 2. ML & Data Engineering
- [x] Created high-fidelity synthetic data generators (seed-fixed).
- [x] Trained and calibrated XGBoost propensity model (0.75+ AUC).
- [x] Engineered "Conflict Accounts" to test governance workbench logic.

### 3. Dashboard UI Upgrade (Premium)
- [x] Replaced simple linear UI with a full "Agent Mesh" SVG visualization.
- [x] Implemented Algoleap Premium branding (colors, typography, spacing).
- [x] Upgraded Response Cards with bucket badges, rationale boxes, and scores.
- [x] Improved Agent Logs with status indicators and micro-spacing.

### 4. Interactive Refinement
- [x] Added interactive POC modes (Targeting, Planning, Whitespace).
- [x] Implemented signal-driven "Next Best Action" synthesis (LLM-directed).
- [x] Replaced deterministic mappings with context-aware NBA generation.
- [x] Humanized account results (Names vs IDs in headers).
- [x] Optimized log sequentiality with a promise-based typewriter queue.

### 5. Propensity Calibration & Logic (v2)
- [x] Expanded feature vector from 8 &rarr; 9 features (Added **Revenue Concentration**).
- [x] Retrained and recalibrated XGBoost model to support expanded telemetry.
- [x] Implemented **Thematic Weighting** (60/80/100) in Reasoning Agent prompts.
- [x] Re-synced runtime and training data generation for deterministic accuracy.

### 6. Resilience & Framework Hardening
- [x] Transitioned to **Strict Online-Only** architecture (removed Ollama fallbacks).
- [x] Migrated 100% of the mesh to **LangChain & LangGraph StateGraph**.
- [x] Implemented **Exponential Backoff Retries** (Tenacity) across all graph nodes.
- [x] Implemented **Global Semaphore** (Rate Limiter) for LLM concurrency control.
- [x] Verified explicit failure reporting and cryptographic audit parity.

### Phase 2: Account Planning (POC 2)
- [x] Implement `Brief Agent LLM` (POC 2) in repo-root `app/modules/planning/brief_agent.py`.
- [x] Implement `Call Plan Agent` (POC 2) in `app/modules/planning/call_plan_agent.py` (OpenRouter via `run_planning_chain`; tracker id **`ag-call`**).
- [x] Unified dashboard: POC2 tab, mesh dimming, live SSE logs; call plan merged after brief in `planning_orchestrator.py`.

### Phase 3: Whitespace Analysis (POC 3)
- [x] Whitespace scoring, k-means clustering, and **Campaign** LLM agent in `app/modules/whitespace/` (telemetry **`ag-camp`**; scoring stage **`ag-ml`**).
- [x] POC3-specific weights and validation in `app/modules/whitespace/constants.py` and `validation_agent.py` (see [`whitespace/requirements/POC3_Requirements_v3.md`](../whitespace/requirements/POC3_Requirements_v3.md)).

### Phase 4: Integration
- [x] Single mesh dashboard + `POST /execute_mission` (POC 1–3) + stepwise `/run/poc1|2|3` (repo-root `app/main.py`).
- [ ] Mock Snowflake/CRM connectors for "Real Data" demo narrative.
- [ ] Final Governance Workbench review loop implementation (UI + tray).
