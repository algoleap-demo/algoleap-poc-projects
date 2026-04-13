# IQ-EQ Agent Mesh: Context & Standards

## Current Status: Unified repo (root `app/`) is authoritative
The **canonical** implementation for POC 1–3 lives in the **workspace root**: [`app/`](../app/), [`data/raw/`](../data/raw/), with the dashboard at [`app/static/`](../app/static/). This `targetingtriage/` folder remains a **reference copy** of POC1-era assets (generators, requirements, `IQ_EQ_Agent_Mesh_2.html`); new work should land in the root app unless you are maintaining this subtree deliberately.

**As of 2026:** POC 1 (targeting), POC 2 (planning), and POC 3 (whitespace) are integrated in root `app/main.py` (LangGraph full mission + stepwise `/run/poc*` routes). See repo-root [`context.md`](../context.md) and [`plan.md`](../plan.md).

This document still establishes **design standards** (Algoleap Premium, mesh semantics) shared with the unified dashboard.

## 1. Project Mission
To transform IQ-EQ's targeting and triage process into a high-fidelity, multi-agent agentic mesh. The system automates the ingestion of account data, scoring for propensity, contextual reasoning, and resolving "Next Best Actions" (NBA) for relationship managers.

## 2. Technical Stack
- **Backend**: Python 3.11+, FastAPI (Uvicorn), Pydantic (Schema Validation).
- **Machine Learning**: XGBoost (Propensity Scorer) using `scikit-learn` and `CalibratedClassifierCV`.
- **Reasoning Layer**: Agentic Blueprint Router (LLM) for contextual bucket assignment and rationale generation.
- **Frontend**: Single-page application (SPA) using Vanilla HTML5, CSS3, and JavaScript.
- **Visualization**: Complex interactive SVG for Agent Mesh status tracking with support for multi-agent pod transitions.
- **Orchestration**: LangGraph `StateGraph` in **repo-root** [`app/main.py`](../app/main.py): `targeting → planning → whitespace` for a full mission; POC1-only linear pipeline remains in [`app/modules/targeting/targeting_orchestrator.py`](../app/modules/targeting/targeting_orchestrator.py).


## 3. Design Standards (Algoleap Premium)
All UI components must adhere to the high-fidelity Algoleap aesthetic:
- **Color Palette**: 
  - Primary Background: `#F8FAFC` (Light) / `#0F172A` (Dark Mode ready).
  - Brand Primary: `#2ECC71` (Green).
  - Accent Blue: `#3B82F6` (Orchestration).
  - Borders: `#E2E8F0` / `#E5E7EB`.
- **Typography**: 
  - Brand/Headers: `Outfit` (Bold, modern).
  - Body/Data: `Inter` (High readability).
  - Logs/Monospace: `JetBrains Mono`.
- **UI Components**:
  - **SVG Mesh**: Horizontal "Master Control" Orchestrator bar at the top with a vertical agent pool below.
  - **Flow Dynamics**: 
    - **Initiate Path**: Direct green arrow from Master Control &rarr; Data Layer.
    - **Return Payload**: Dashed side-loop from Formatting &rarr; Master Control for lifecycle completion.
  - **Agent Status**: Clean rects with `ag-active` (pulse yellow) and `ag-completed` (fill green) states.
  - **Response Cards**: 
    - Header: Bold Account Name + (ID).
    - Badge: Positioned top-right, color-coded (`bucket-A`: green, `bucket-B`: amber, `bucket-C`: grey).
    - Rationale: Contained in a light-grey padded box.
    - Score: Bottom-left in bold green.
  - **Modals**: Glassmorphic overlay, interactive NBA details with explicit "Why this action?" reasoning.

## 4. Agent Mesh Architecture (LangGraph)
The pipeline is implemented as a formal **StateGraph** with a centralized `AgentMeshState`. Each agent represents a functional **Node** in the graph:

1. **Orchestration Agent (Graph Entry)**: Compiles the graph, initializes state, and manages the trace/audit lifecycle.
2. **Data Agent (Node)**: Ingests and joins 1:N account relationships.
3. **ML Scoring Agent (Node)**: Runs the 9-feature XGBoost model for propensity scoring.
4. **Reasoning Agent (Node)**: Contextual LLM assessment via **LangChain (LCEL)** using thematic weights (60/80/100).
5. **Validation Agent (Node)**: Conflict detection and automated governance queueing.
6. **Formatting Agent (Node)**: Finalizes the pydantic payload and maps deterministic NBAs.

### 4.1 Decision Standards
- **Propensity Thresholds**:
  - High Propensity (Bucket A): > 0.70
  - Mid Propensity (Bucket B): 0.30 - 0.70
  - Low Propensity (Bucket C): < 0.30
- **Thematic Weights**: 
  - **60% Historical**: Performance metrics (Win Rate, Deal Size).
  - **80% Firmographic**: Fit and Size (Revenue Concentration, Segment).
  - **100% Timing**: Active Signals (Fund Launches, Conference Attendance).

### 4.2 Resilience & Reliability
To ensure production-grade stability, the Mesh implements several fault-tolerance patterns:
- **Exponential Backoff Retries**: Every agent node is wrapped in a `tenacity` retry policy (3 attempts) to handle transient network or API failures.
- **Concurrency Control (Rate Limiting)**: A global `asyncio.Semaphore(3)` restricts the number of simultaneous LLM calls, protecting our API quotas from exhaustion.
- **Strict Online Execution**: To ensure absolute auditability, local LLM fallbacks (e.g., Ollama) and hardcoded "fail-soft" heuristics are prohibited.
  - If online APIs (Gemini, OpenAI, Groq) are unreachable after 3 retries, the pipeline must **fail explicitly**.
- **Cryptographic Traceability**: 
  - All inter-agent communication is hashed (SHA-256).
  - Every `run_id` provides a tamper-evident audit trail in `logs/audit.jsonl`.

### Agent Messaging Standards
Every agent must emit events via SSE (`ProgressTracker`):
```json
{
  "agent_name": "ag-name",
  "status": "START|END",
  "run_id": "uuid",
  "message": "Human readable progress update"
}
```
To maintain a premium feel, the following standards are enforced:
- **Log Rendering**: Sequential, promise-based log queue ensures messages type out one-by-one at 15ms/char, perfectly synchronized with SVG state transitions.
- **Visual Feedback**: Independent scroll containers for agent logs to prevent workspace jitter and a 50/50 split for balanced data/mesh viewing.

- [/] Final Governance Workbench review loop implementation (Manual Review Tray).
- [x] Aesthetic Overhaul: Integrated "Algoleap Premium Light" design system across the unified dashboard.
- [x] Unified Master Orchestrator: Centralized state management for cross-agent lifecycle control.

## 5. Directory Structure
- `/app`: Implementation of agents, schemas, and core logic.
- `/data`: Synthetic training (2.5k) and runtime (50) datasets.
- `/models`: Pickled ML models and score distribution artifacts.
- `/scripts`: Data generation and model training utilities.
- `/plan`: Detailed execution plans and history.
