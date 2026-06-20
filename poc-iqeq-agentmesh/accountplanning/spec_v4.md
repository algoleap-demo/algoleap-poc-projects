# POC 2 Technical Specification — Account Planning (v4.1)

## 01 Executive Summary
This specification aligns the Account Planning POC with the **Unified IQ-EQ Agent Mesh Dashboard**. It mandates a "Zero Safety Net" online-only architecture using **LangGraph StateGraph** and consistent resilience patterns, integrated into a multi-module interface.

## 02 Architectural Alignment (Unified Mesh)
The POC 2 pipeline inherits the following standards from the Unified Foundation:
- **Orchestration**: `StateGraph` (LangGraph). Transitions are triggered automatically upon POC selection in the dashboard.
- **Resilience**: Every agent node MUST wrap its execution in the global `LLM_SEMAPHORE` (limit: 3) and `tenacity` retry policy.
- **Connectivity**: **Strict Online-Only**. No local LLM fallbacks. Failures must be reported explicitly to the dashboard status node.
- **Unified UI**: Integrated into the shared dashboard view-bar. Selection of "POC 2" triggers an immediate pipeline run (refresh-on-click).

## 03 Agent Definitions (Modular Mesh)

### 03.1 Orchestration Agent
- **State**: `PlanningState` (TypedDict) including `trace_id`, `telemetry`, `errors`.
- **Logic**: Manages the transition from POC 1 (Targeting) to POC 2 (Planning) using shared state.

### 03.2 Whitespace Scoring Agent (Logic)
- **Calculation**: Computes `api_score` using the 50/30/20 tripartite weighted formula.
- **ML Integration**: Cross-references the `ml_score` from POC 1 via the shared graph state.

### 03.3 Account Brief Agent (LLM)
- **Hardening**: Uses `LLM_SEMAPHORE` to limit concurrent calls.
- **Constraint**: Generates markdown-ready brief summaries and JSON-structured account metadata.

### 03.4 Validation Agent (Governance)
- **Conflict detection**: Flags "High Propensity + Zero Whitespace" scenarios.
- **Human-In-The-Loop**: Flagged accounts are routed to the **Governance Workbench** for manual override/approval before final formatting.

## 04 Shared Design System
- **Context-Aware Tabs**: UI switches automatically to "Account Briefs & Plans" upon POC 2 completion.
- **Visual Lineage**: SVG mesh nodes must pulse with a blue glow (`ag-active`) during planning execution.

---

## 05 Data Schema Extensions
| File | Cardinality | Primary Key | Join Key |
|---|---|---|---|
| `contacts.csv` | 1:N | `contact_id` | `account_id` |
| `account_product_matrix.csv` | M:N | `join_id` | `account_id`, `product_id` |
| `product_catalog.csv` | Catalog | `product_id` | - |
