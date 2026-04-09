---
name: agent-pipeline
description: Agent contracts, 100% autonomous flow, and signal-driven confidence rules.
---

# Agent Pipeline Skill (v2)

This skill documents the autonomous agent mesh architecture where decisions are synthesized from customer signals rather than deterministic rules.

## Autonomous Architecture
The pipeline follows a linear command-primary flow:
1. **Orchestration Agent (Header)**: Horizontal command center. Initiates the lifecycle and receives the final return payload.
2. **Data Agent**: Ingests 1:N signal data from CRM/Systems.
3. **Scoring Agent (ML)**: Generates a propensity score and a **signal-driven confidence level**.
4. **Reasoning Agent (LLM)**: Performs contextual analysis and **synthesizes a bespoke strategy (NBA)**.
5. **Validation Agent**: Governs the output for ML/LLM conflicts.
6. **Formatting Agent**: Acts as a pass-through for the LLM results, assembling the final Pydantic payload.

## Core Breakthroughs

### 1. 100% Signal-to-Action (NBA Synthesis)
**Contract Change**: The reasoning agent is no longer limited to "A/B/C" buckets. It is now responsible for generating the entire **Next Best Action** (NBA) object.
- **Dynamic Advice**: NBA action types (`call`, `meeting`, `email`) and descriptions must be varied based on the specific signals (e.g., segment, country, launch status).
- **Rule Removal**: Deterministic mappings like `BUCKET A -> CALL` are prohibited. The LLM must reason through *why* a call or email is appropriate.

### 2. Signal-Driven Confidence Level
The `confidence_level` must be an honest reflection of the model's certainty, derived from the probability spread:
- **Formula**: `confidence = abs(prob - 0.5) / 0.5` (scaled to represent certainty from the 0.5 decision boundary).
- This ensures the UI reflects when a model is "unsure," triggering higher scrutiny from the user.

## Agent Contracts (Updated)

### Reasoning Agent (`app/agents/reasoning_agent.py`)
- **Input**: ML Scores + Raw Customer Signals.
- **Output**: `priority_bucket`, `rationale_text`, and a full `NBAAction` object.
- **Constraint**: Must use specific signals (Country, Segment, Launch) to tailor the suggested action.

### Formatting Agent (`app/agents/formatting_agent.py`)
- **Input**: The full bundle of agent outputs.
- **Responsibility**: Pure schema validation and structural assembly. No logic-based overrides.

## Output Schema (Full Autonomy)
```json
{
  "account_id": "Nexus-EU",
  "priority_bucket": "A",
  "ml_score": 0.96,
  "confidence_level": 0.92,
  "rationale_text": "Bespoke LLM rationale...",
  "nba_actions": [
    {
      "action_type": "meeting",
      "description": "Schedule Paris Sector Review",
      "reasoning": "High propensity in the FR market for this segment.",
      "due_in_days": 3
    }
  ]
}
```

## Critical Rules
1. **Zero Hardcoding**: No deterministic NBA lookup tables are allowed.
2. **Context-Awareness**: Every action suggested must be justifiable by the input signals.
3. **Synchronized Mesh**: Agent status updates must be coupled with the sequential log typewriter for democratic transparency.
