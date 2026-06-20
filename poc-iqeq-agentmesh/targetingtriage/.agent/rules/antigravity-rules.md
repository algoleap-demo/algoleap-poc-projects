---
description: IQ-EQ POC project rules — auto-applied to all Antigravity sessions
---

# IQ-EQ Mission Compliance
This project is governed by the **Antigravity Mission Standards**. 
Authoritative Manifest: 👉 **[.agent/MISSION_STANDARDS.md](file:///.agent/MISSION_STANDARDS.md)**

# IQ-EQ POC Context
- Client: IQ-EQ
- POC type: GenAI-Agent (Targeting & Triage / Account Planning)
- Stack: FastAPI + Vanilla JS/CSS + LangChain/LangGraph
- Persona: Antigravity

# Scope Boundaries
- Only create or modify files inside `app/`, `data/`, and `logs/`.
- Do not modify trained model files in `models/`.
- All inter-agent data must be Pydantic-validated.
- Do NOT hardcode deterministic Next Best Actions.

# Naming Conventions
- Python functions: `snake_case`
- API routes: `/api/[resource]` — plural nouns, no verbs.
- Agent Logs: `ag-[shortname]` (e.g., `ag-orch`, `ag-data`).

# Demo Data Rules
- All data is 100% synthetic.
- Raw datasets go in `data/raw/`.
- Processed datasets go in `data/processed/`.

# UI/UX Excellence
- Typography: `Outfit` (Headers), `Inter` (Body).
- Layout: 50/50 Balanced Split.
- Animations: 15ms sequential typewriter效果.
