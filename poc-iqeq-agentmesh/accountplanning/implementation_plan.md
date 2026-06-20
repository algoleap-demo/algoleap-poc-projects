# Implementation Plan — POC 2: Account Planning (v2.0)

## Goals
Implement a resilient, LangGraph-powered Account Planning mesh that reuses the POC 1 propensity backbone and extends it with Whitespace analysis and LLM-generated briefs, fully integrated into the Unified Dashboard.

## Phase 1: Data Expansion & Core Alignment
- [x] Symlink `models/xgb_propensity_v1.pkl` from POC 1.
- [ ] Create `data_gen_poc2.py` to generate `contacts.csv` and `account_product_matrix.csv`.
- [ ] Update `targetingtriage/app/schemas.py` to include `PlanningState` for the Unified Mesh.
- [ ] Establish "Metadata Lineage": Ensure POC 2 agents ingest `ml_score` and `priority_bucket` from POC 1 results.

## Phase 2: Agent Node Development
- [ ] **Data Agent**: Update to load and join the 3 new POC 2 CSV files via shared `DataManager`.
- [ ] **Whitespace Agent**: Implement deterministic scoring (Expected Revenue + Potential Buckets).
- [ ] **Brief Agent**: Implement `LCEL` chain with `LLM_SEMAPHORE` (limit: 3) for structured brief generation.
- [ ] **Validation Agent**: Implement "Conflict Matrix v2" with explicit human review flags.

## Phase 3: Orchestration & Unified UI Sync
- [ ] Define the `planning` node in the main `StateGraph` in `targetingtriage/app/orchestration_agent.py`.
- [x] **Auto-Trigger**: Implement `onclick="pick(2)"` to automatically call `start()` in `index.html`.
- [ ] **Context-Aware Tabs**: Implement auto-switching to the "Account Briefs & Plans" tab upon mission completion.
- [ ] **Governance Workbench**: Build the human-review modal for resolving ML vs LLM conflicts.

## Phase 4: Verification & Audit
- [ ] Run End-to-End "Unified Mission" for top 5 Priority A accounts.
- [ ] Verify "Auto-Refresh" behavior: Pipeline must re-run every time the POC 2 button is clicked.
- [ ] Audit check: Ensure `logs/audit.jsonl` contains SHA-256 state hashes for planning decisions.
- [ ] Secure connectivity: Verify explicit error reporting when online LLM access is interrupted.
