# IQ-EQ Agent Mesh: Context & Standards

This document establishes the technical, architectural, and design standards for the Algoleap IQ-EQ Agent Mesh POC.

## 1. Project Mission
To transform IQ-EQ's targeting and triage process into a high-fidelity, multi-agent agentic mesh. The system automates the ingestion of account data, scoring for propensity, contextual reasoning, and resolving "Next Best Actions" (NBA) for relationship managers.

## 2. Technical Stack
- **Backend**: Python 3.11+, FastAPI (Uvicorn), Pydantic (Schema Validation).
- **Machine Learning**: XGBoost (Propensity Scorer) using `scikit-learn` and `CalibratedClassifierCV`.
- **Reasoning Layer**: Agentic Blueprint Router (LLM) for contextual bucket assignment and rationale generation.
- **Frontend**: Single-page application (SPA) using Vanilla HTML5, CSS3, and JavaScript.
- **Visualization**: Complex interactive SVG for Agent Mesh status tracking.

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

## 4. Agent Mesh Architecture
The pipeline follows a linear 6-agent contract:
1. **Orchestration Agent**: Entry point, generates `run_id`, manages state.
2. **Data Agent**: Ingests and joins 1:N account relationships.
3. **ML Scoring Agent**: Runs the 8-feature XGBoost model for propensity.
4. **Reasoning Agent**: Contextual LLM assessment for priority buckets and **bespoke NBA synthesis**.
5. **Validation Agent**: Conflict detection between ML and LLM scores.
6. **Formatting Agent**: Finalizes the pydantic payload and maps the LLM-suggested actions.

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


## 5. Directory Structure
- `/app`: Implementation of agents, schemas, and core logic.
- `/data`: Synthetic training (2.5k) and runtime (50) datasets.
- `/models`: Pickled ML models and score distribution artifacts.
- `/scripts`: Data generation and model training utilities.
- `/plan`: Detailed execution plans and history.
