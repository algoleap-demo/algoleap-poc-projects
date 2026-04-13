# IQ-EQ Unified Agent Mesh

## Strategic AI Targeting, Planning, and Whitespace Analysis

This workspace contains the unified codebase for the IQ-EQ Agentic POCs. All agents are built on a hardened LangGraph foundation, ensuring production-grade resilience and auditability.

**Living docs:** [ARCHITECTURE.md](ARCHITECTURE.md) (stakeholder architecture — diagrams, formulas, LLMs, algorithms), [context.md](context.md) (integration map), [plan.md](plan.md) (completed implementation plan), [HANDOVER.md](HANDOVER.md) (runbook & handover). POC3 detail: [whitespace/context.md](whitespace/context.md), [whitespace/plan.md](whitespace/plan.md).

### Architecture overview
The system uses a **StateGraph** architecture where each functional requirement is a modular "Agent Node".

1.  **POC 1: Targeting & Triage**: (Completed) - ML + LLM mesh for account prioritization.
2.  **POC 2: Account Planning**: (Completed in unified `app/`) - OpenRouter brief + call plan, validation, formatting.
3.  **POC 3: Whitespace Analysis**: (Implemented) - Matrix whitespace scoring, k-means clusters, OpenRouter campaign briefs. See `whitespace/README.md` and `POST /analyze_whitespace`.

### Resilience core (`app/core/`)
All POCs inherit the following hardening features:
*   **Rate Limiting**: Global `LLM_SEMAPHORE` (max 3 concurrent calls).
*   **Fault Tolerance**: `tenacity` retries with exponential backoff on all nodes.
*   **Cryptographic Audit**: SHA-256 state hashing logged to `logs/audit.jsonl`.
*   **Telemetry**: Integrated latency tracking per agent node.

### Design system
All dashboards share the **Algoleap Premium Theme** via `app/static/shared_styles.css`. This includes:
*   Glassmorphic panels.
*   Synchronized SVG mesh animations.
*   Typewriter log streaming.

### Getting started
1. Install dependencies: `pip install -r requirements.txt`
2. Start the unified server: `python -m uvicorn app.main:app --port 8000`
3. Open the **Unified Agent Mesh** dashboard at `http://localhost:8000/` —50/50 architecture diagram (from `IQ_EQ_Agent_Mesh_2.html`) and live `/events` logs. Use **Run POC 1 / 2 / 3** (stepwise) or **Full mission 1→2→3**. Requires API keys in `.env` (OpenRouter for POC2/3 LLM; POC1 reasoning uses configured providers in `llm_client`).

---
Copyright © 2026 Algoleap. Internal IQ-EQ Demonstration.
