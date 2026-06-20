# POC1 — Targeting & Triage Agent Mesh

## AI-powered account prioritisation for IQ-EQ Continental Europe FAM/PIAO

An end-to-end agentic pipeline that triages accounts using **XGBoost (ML)** for propensity scoring, **LLM** for contextual reasoning, and deterministic rules for **Next Best Action (NBA)** resolution.

### 🚀 Interactive Dashboard

This POC features a high-fidelity, Algoleap-themed dashboard for real-time monitoring of the agent pool.

1. **Start the server**:
   ```bash
   $env:PYTHONPATH="."; python app/main.py
   ```
2. **Access the UI**: Go to [http://localhost:8000](http://localhost:8000)
3. **Trigger Pipeline**: Click the "TRIGGER PIPELINE" button to see the 6-agent mesh execute in sequence with real-time log streaming and interactive flowchart highlighting.

---

### 🛠️ Quick Start (API Only)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000

# Trigger the pipeline
curl -X POST http://localhost:8000/score_accounts
```

---

### 🛡️ Architecture & Governance (LangGraph)

The system is built as a formal **StateGraph** powered by **LangGraph**, providing a robust, fault-tolerant backbone for agent orchestration:

```
User → LangGraph Orchestrator
          → [NODE] Data Agent
          → [NODE] Scoring Agent (ML)
          → [NODE] Reasoning Agent (LangChain LLM)
          → [NODE] Validation Agent
          → [NODE] Formatting Agent
User ← Output State
```

**Key Features:**
- **LangChain/LangGraph Foundation**: Standardized multi-agent orchestration for easier scalability into POC 2 and POC 3.
- **Conflict Detection**: The Validation Agent flags disagreement between statistical ML scores and contextual LLM reasoning.
- **Audit Trail**: Every state transition is cryptographically hashed (SHA-256) into `logs/audit.jsonl`.
- **NBA Resolution**: Deterministic rule-based lookup based on priority buckets to ensure 100% auditability.

---

### 📂 Project Layout

```
app/                    # Core application code
  agents/               # 5 specialist agents (Data, ML, LLM, Valid, Format)
  static/               # Frontend Dashboard (HTML/CSS/JS)
  features.py           # Single Source of Truth for feature engineering
  orchestration_agent.py# Pipeline controller & Audit logger
  progress_tracker.py   # SSE broadcaster for UI updates
data/
  training/             # 2,500 training accounts (XGBoost)
  synthetic/            # 50 demo accounts (Dashboard)
models/                 # Trained XGBoost pickle + validation artifacts
logs/                   # Audit trail & Governance queue (JSONL)
tests/                  # E2E, Schema, and Feature Parity tests
```

### 📋 Out of Scope
- Real CRM connectors (Salesforce/Dynamics)
- User Authentication
- Continuous Retraining Loop
- Multi-POC orchestration (handled by Single Orchestrator in v1)
