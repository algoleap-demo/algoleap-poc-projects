---
name: agent-pipeline
description: Agent contracts, pipeline flow, and boundary rules for the POC1 six-agent linear pipeline
---

# Agent Pipeline Skill

This skill documents the linear pipeline architecture, each agent's contract (inputs, outputs, constraints), and the rules governing agent boundaries.

## Pipeline Architecture

```
User Intent
    │
    ▼
┌──────────────────┐
│  Orchestration    │ ← generates pipeline_run_id, plans sequence
│  Agent            │
└────────┬─────────┘
         │ single outbound delegation
         ▼
┌──────────────────┐
│  Data Agent      │ ← loads + joins 6 CSVs, validates referential integrity
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Scoring Agent   │ ← calls features.py, loads XGBoost pickle, emits scores
│  (ML)            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Reasoning Agent │ ← invokes LLM router, assigns priority bucket + rationale
│  (LLM)           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Validation Agent│ ← detects ML vs LLM conflicts, logs to governance queue
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Formatting Agent│ ← resolves NBA, validates schema, assembles JSON payload
└────────┬─────────┘
         │ returns to Orchestration
         ▼
┌──────────────────┐
│  Orchestration    │ ← delivers final response to user
│  Agent            │
└──────────────────┘
```

**Key design:** Linear pipeline. No hub-and-spoke. No Planner Agent. The Orchestration Agent handles planning.

## Agent Contracts

### 1. Orchestration Agent (`app/orchestration_agent.py`)

| Field | Detail |
|---|---|
| **Input** | User intent + filters (country, segment, date range) |
| **Responsibility** | Generates `pipeline_run_id` (UUID4), delegates to Data Agent, receives final payload from Formatting Agent, delivers to user |
| **Output** | Final structured JSON response |
| **Audit** | Writes pipeline start/end events to `logs/audit.jsonl` |

### 2. Data Agent (`app/agents/data_agent.py`)

| Field | Detail |
|---|---|
| **Input** | User filters (country, segment, date range) |
| **Responsibility** | Loads all 6 CSVs from `data/synthetic/`, validates referential integrity (no orphaned FKs) |
| **Output** | Validated raw dataset (multi-table dict) |
| **Passes to** | Scoring Agent |

**6 CSV files loaded:**
- accounts.csv (1:1 master)
- opportunities.csv (1:N, 4 per account)
- snowflake_metrics.csv (1:1)
- external_funds.csv (1:N, ~60% coverage)
- conferences.csv (catalog, ~25)
- conference_attendance.csv (M:N join, ~2.5 per account)

### 3. Scoring Agent (`app/agents/scoring_agent.py`)

| Field | Detail |
|---|---|
| **Input** | Validated raw dataset from Data Agent |
| **Responsibility** | Calls `app/features.py` → `compute_features()` to aggregate raw 1:N data into per-account feature vectors. Loads XGBoost pickle and predicts. |
| **Output Fields** | `propensity_score` (float, 0-1) · `confidence_level` (float, 0-1) |
| **Passes to** | Reasoning Agent |

**Critical runtime checks:**
- Assert `df.columns.tolist() == pickle["feature_names"]`
- Fail loudly on mismatch

### 4. Reasoning Agent (`app/agents/reasoning_agent.py`)

| Field | Detail |
|---|---|
| **Input** | `propensity_score` + `confidence_level` + business context (launch_indicator, conference signals, segment, country) |
| **Responsibility** | Assigns priority bucket (A/B/C), generates plain-English rationale |
| **Output Fields** | `priority_bucket` (A/B/C) · `rationale_text` (string) |
| **Passes to** | Validation Agent |
| **LLM Provider** | Multi-provider router from `agentic-ai-blueprint`; default model via env var |

**Prompt template (locked starting point):**
```
You are the Reasoning Agent for IQ-EQ FAM/PIAO account triage.

Given an account with:
- propensity_score: {ml_score} (0-1, from XGBoost)
- confidence_level: {confidence}
- launch_indicator: {launch}
- tier_1_conf_count: {tier_1_count}
- segment: {segment}, country: {country}

Assign a priority bucket and write a one-sentence rationale.

Rules:
- Bucket A: strong commercial signal AND contextual catalyst
- Bucket B: moderate signal OR mixed context
- Bucket C: weak signal AND no contextual catalyst
- Do NOT recalculate the propensity score
- Rationale must reference at least one specific signal

Return strict JSON: {"priority_bucket": "A|B|C", "rationale_text": "..."}
```

### 5. Validation Agent (`app/agents/validation_agent.py`)

| Field | Detail |
|---|---|
| **Input** | All per-account data from Reasoning Agent (including ML scores + LLM bucket) |
| **Responsibility** | Detects conflicts between ML and LLM outputs. NEVER suppresses conflicts. |
| **Output Fields** | `conflict_flag` (bool, per account) |
| **Passes to** | Formatting Agent (pipeline does NOT block on conflicts) |

**Conflict detection rule:**
```python
ML_HIGH_THRESHOLD = 0.70
ML_LOW_THRESHOLD  = 0.30

def is_conflict(ml_score: float, llm_bucket: str) -> bool:
    ml_level = "High" if ml_score >= ML_HIGH_THRESHOLD else \
               "Low"  if ml_score <= ML_LOW_THRESHOLD  else "Medium"
    llm_level = LLM_BUCKET_TO_LEVEL[llm_bucket]
    return (ml_level, llm_level) in {("High", "Low"), ("Low", "High")}
```

**Governance hook:** `conflict_flag=True` accounts appended to `logs/governance_queue.jsonl`

### 6. Formatting Agent (`app/agents/formatting_agent.py`)

| Field | Detail |
|---|---|
| **Input** | All per-account data (scores, bucket, conflict flag, rationale) |
| **Responsibility** | (1) Resolve NBA via deterministic rules, (2) Validate all fields via Pydantic, (3) Assemble strict JSON, (4) Return to Orchestration Agent |
| **Output** | Complete pipeline response JSON |
| **Returns to** | Orchestration Agent |

**NBA Resolution (deterministic):**

| Bucket | action_type | description | due_in_days |
|---|---|---|---|
| A | call | Call this week | 5 |
| B | send_link | Send targeted product brief | 10 |
| C | schedule | Schedule quarterly check-in | 90 |

## Output Schema

```json
{
  "pipeline_run_id": "uuid4",
  "generated_at": "2026-04-08T12:34:56Z",
  "model_version": "xgb_propensity_v1+router_v1",
  "accounts": [
    {
      "account_id": "ACME-EU-90001",
      "priority_bucket": "A",
      "ml_score": 0.84,
      "confidence_level": 0.91,
      "conflict_flag": false,
      "rationale_text": "Strong win rate combined with a new fund launch in the last 60 days.",
      "nba_actions": [
        {"action_type": "call", "description": "Call this week", "due_in_days": 5}
      ]
    }
  ]
}
```

**Required fields per account:** account_id, priority_bucket, ml_score, confidence_level, conflict_flag, rationale_text, nba_actions

## Decision Layer Separation

| Layer | Agent | Role | Hard Constraint |
|---|---|---|---|
| ML | Scoring Agent | Statistical propensity from historical patterns | Does NOT use contextual signals |
| LLM | Reasoning Agent | Contextual reasoning, priority bucket assignment | Does NOT recalculate ML scores |
| NBA | Formatting Agent | Deterministic rule lookup from priority_bucket | NOT an LLM inference |
| Conflict | Validation Agent | ML vs LLM disagreement detection | NEVER suppresses conflicts |

## Audit Trail

Every agent invocation writes one line to `logs/audit.jsonl`:
```json
{"run_id": "...", "agent": "data_agent", "input_hash": "...", "output_hash": "...", "ts": "...", "duration_ms": 42}
```

## Critical Rules

1. **No agent may skip another** — the pipeline is strictly linear
2. **Reasoning Agent must NOT recalculate ML scores** — it receives them and adds semantics
3. **NBA is rule-based, not LLM-based** — auditability under ISO 42001
4. **Conflicts are never suppressed** — always surfaced, always logged
5. **Pydantic enforces schema** — Formatting Agent rejects any payload with missing/invalid fields
6. **confidence_level flows through unused in v1** — reserved for v2 tiebreaker/flag use
