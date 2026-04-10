# IQ-EQ Unified Agent Mesh

## Strategic AI Targeting, Planning, and Whitespace Analysis

This workspace contains the unified codebase for the IQ-EQ Agentic POCs. All agents are built on a hardened LangGraph foundation, ensuring production-grade resilience and auditability.

### 🏛️ Architecture Overview
The system uses a **StateGraph** architecture where each functional requirement is a modular "Agent Node".

1.  **POC 1: Targeting & Triage**: (Completed) - ML + LLM mesh for account prioritization.
2.  **POC 2: Account Planning**: (In Development) - Briefly and Call Plan agents.
3.  **POC 3: Whitespace Analysis**: (Planned) - Cross-sell and Upsell intelligence.

### 🛡️ Resilience Core (`app/core/`)
All POCs inherit the following hardening features:
*   **Rate Limiting**: Global `LLM_SEMAPHORE` (max 3 concurrent calls).
*   **Fault Tolerance**: `tenacity` retries with exponential backoff on all nodes.
*   **Cryptographic Audit**: SHA-256 state hashing logged to `logs/audit.jsonl`.
*   **Telemetry**: Integrated latency tracking per agent node.

### 🎨 Design System
All dashboards share the **Algoleap Premium Theme** via `app/static/shared_styles.css`. This includes:
*   Glassmorphic panels.
*   Synchronized SVG mesh animations.
*   Typewriter log streaming.

### 🚀 Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Start the unified server: `python -m uvicorn app.main:app --port 8000`
3. Access the Targeting Triage POC at `http://localhost:8000/`

---
Copyright © 2026 Algoleap. Internal IQ-EQ Demonstration.
