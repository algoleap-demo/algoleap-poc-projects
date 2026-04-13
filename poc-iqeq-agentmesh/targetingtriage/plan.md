# Project Plan: IQ-EQ Agent Mesh Dashboard

This document tracks the milestones, completed work, and future roadmap for the Targeting & Triage Agent Mesh.

## Current Status: Phase 1 Stable | Phase 2 Transition (Active)
The core pipeline for POC 1 is fully functional. We are currently migrating the strategic mesh (POC 2) into the unified app structure.


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
- [x] Implement `Brief Agent LLM` (POC 2) in `app/modules/planning/brief_agent.py`.
- [x] Implement `Call Plan Agent` (POC 2) in `app/modules/planning/call_plan_agent.py`.
- [/] Update Mesh interactions to reflect POC 2 active path (Unified Dashboard Overhaul).


### Phase 3: Whitespace Analysis (POC 3)
- [ ] Implement `Campaign Agent` for whitespace clustering.
- [ ] Integrate market signal scoring (POC 3 specific weights).

### Phase 4: Integration
- [ ] Mock Snowflake/CRM connectors for "Real Data" demo.
- [ ] Final Governance Workbench review loop implementation.
