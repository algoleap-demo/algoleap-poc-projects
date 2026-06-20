# POC2 — Account Planning Co-Pilot
## Agentic Rapid Prototype — Requirements v3.0

| Field | Details |
|---|---|
| Document Type | POC Requirements Specification — Rapid Prototype |
| Version | 3.0 — April 2026 |
| Status | Approved for Implementation |
| Prepared By | AI Architecture Team |
| Classification | Confidential — Internal Use Only |
| Supersedes | v2.0 |
| Builds On | POC1 v3 — reuses data backbone, shared features.py, trained XGBoost pickle, and infrastructure patterns |
| Key Changes v3 | Planner Agent removed; Orchestration Agent handles planning (linear pipeline, consistent with POC1 v3). LLM provider locked to **OpenRouter** via multi-provider router. Copilot UX deferred to Phase 2. Three POC2-specific files added with realistic 1:N cardinality. Shared training (2,500 accounts) and runtime (50 accounts) datasets aligned with POC1. All thresholds, prompts, schemas, and stub strategies locked. |

---

## 01 Overview

This document defines the **rapid prototype** of the IQ-EQ Account Planning Co-Pilot for Continental Europe FAM/PIAO. The system generates structured account briefs, call plans, whitespace summaries, and next-best actions for sales representatives.

The Account Planning Co-Pilot **builds directly on POC1 v3**, reusing its data backbone, trained XGBoost propensity model, and shared `features.py` aggregation layer. Three new data files are added: contacts, account-product matrix, and account plan templates.

The pipeline uses **six agents total**: one Orchestration Agent plus five specialist agents in a linear pipeline. Consistent with POC1 v3, there is no separate Planner Agent — the Orchestration Agent initiates and receives.

**The prototype is designed to:**
- Generate structured, data-driven account briefs for sales representatives
- Produce tailored call plans for key client contacts
- Identify and summarise whitespace opportunities per account
- Recommend next-best actions based on propensity and whitespace scoring
- Provide explainable, auditable AI reasoning for every account
- Deliver all outputs through the Orchestration Agent directly to the user (no Copilot in prototype)

**Out of scope for this prototype:** Copilot UX layer, real CRM/Snowflake connectors, Governance Workbench UI, override workflow, authentication, persistence, retraining loops, production error handling.

---

## 02 Objectives

- Generate professional, data-driven account briefs using LLM synthesis over structured features
- Produce tailored call plans scored by contact influence
- Identify whitespace opportunities per account using the account-product matrix
- Compute an Account Planning Index (API score) that combines propensity, whitespace potential, and strategic priority
- Flag internal consistency conflicts (e.g., high propensity + zero whitespace) for human review
- Support ISO 42001 auditability with structured logging of every agent decision

---

## 03 Agent Definitions

The pipeline uses **six agents total** in a linear flow: Orchestration → Data → Whitespace Scoring → Account Brief (LLM) → Validation → Formatting → Orchestration → User.

### 03.1 Orchestration Agent

| Field | Detail |
|---|---|
| Responsibility | Receives user intent, generates `pipeline_run_id`, delegates to Data Agent (single outbound delegation), receives final payload from Formatting Agent, delivers response to user |
| Input | User intent: account list or filter criteria (country, segment) |
| Output | Final structured response (array of account planning packs) |
| Audit | Writes pipeline start/end events to `logs/audit.jsonl` |

### 03.2 Data Agent

| Field | Detail |
|---|---|
| Responsibility | Loads and joins all CSVs (POC1 files + POC2-specific files). Validates referential integrity. Enforces boundary between raw data and downstream agents. |
| Input Filters | country · segment · account_id list (optional) |
| Data Sources | **From POC1:** accounts · opportunities · snowflake_metrics · external_funds · conferences · conference_attendance. **POC2-specific:** contacts · account_product_matrix · product_catalog (shared with POC3) |
| Output | Validated raw dataset (multi-table dict) — clean, no orphaned FKs |
| Returns To | Whitespace Scoring Agent |
| LLM | None — deterministic data loader |

### 03.3 Whitespace Scoring Agent

| Field | Detail |
|---|---|
| Responsibility | Computes whitespace flags, expected revenue per gap, and total whitespace potential per account using deterministic rules from `account_product_matrix.csv`. Also loads POC1's trained XGBoost pickle and computes propensity scores. |
| Input | Validated raw dataset from Data Agent |
| Key Formulas | `whitespace_flag(a,p) = 1 if has_product=false AND potential_revenue_bucket ∈ {Medium, High}` · `expected_revenue_eur = {Low: 50K, Medium: 150K, High: 300K}` · `total_ws_potential(account) = Σ expected_revenue × whitespace_flag` |
| Propensity | Reuses POC1 pickle (`models/xgb_propensity_v1.pkl`) via shared `features.py`. Same feature order, same calibration. |
| Output Fields | `propensity_score` · `confidence_level` · `whitespace_list` (per account) · `total_ws_potential_eur` · `relationship_depth` · `api_score` |
| API Score | `api_score = 0.5 × propensity_score + 0.3 × normalised(total_ws_potential) + 0.2 × strategic_priority_flag` |
| Design Rationale | Deterministic scoring — no LLM. Reproducible, auditable, fast. |
| Returns To | Account Brief Agent |

### 03.4 Account Brief Agent (LLM)

| Field | Detail |
|---|---|
| Responsibility | Generates the structured 1-page account brief and the call plan per account. This is the only LLM-calling agent in POC2. |
| Input | Account features + scores from Whitespace Scoring Agent + top 3 contacts ranked by `contact_influence` |
| Output Fields | `brief_text` (5 sections: Summary, Relationship & Performance, Whitespace & Upsell, Key Contacts, Recommended Actions) · `call_plan_text` (for top contact) |
| Contact Scoring | `contact_influence = role_weight × seniority_weight × prior_engagement_score` — computed deterministically before LLM invocation |
| LLM Provider | **OpenRouter** via the multi-provider router in `agentic-ai-blueprint`. Default model: `anthropic/claude-3.5-sonnet` or `openai/gpt-4o-mini` — configurable via env var `POC2_LLM_MODEL`. |
| LLM Constraint | Must NOT recalculate scores or invent data. All numbers in the brief must come from structured input. |
| Returns To | Validation Agent |

### 03.5 Validation Agent

| Field | Detail |
|---|---|
| Responsibility | Checks internal consistency between propensity, whitespace, and the LLM-generated brief. Surfaces conflicts — never suppresses them. |
| Conflict Rules | `propensity_score ≥ 0.7 AND total_ws_potential_eur < 50K → conflict_flag=True (high intent, nothing to sell)` · `propensity_score ≤ 0.3 AND total_ws_potential_eur > 500K → conflict_flag=True (big opportunity, low intent)` |
| Output Fields | `conflict_flag` (bool) · `review_notes` (string) |
| ISO 42001 Hook | Flagged accounts appended to `logs/governance_queue.jsonl` (prototype stub) |
| Returns To | Formatting Agent (pipeline does not block on conflicts in prototype) |
| LLM | None — deterministic rule check |

### 03.6 Formatting Agent

| Field | Detail |
|---|---|
| Responsibility | (1) Resolve NBA actions from priority rules. (2) Assemble strict JSON payload. (3) Validate via Pydantic. (4) Return to Orchestration Agent. |
| NBA Resolution | `api_score ≥ 0.75` → Schedule QBR within 7 days · `0.5 ≤ api_score < 0.75` → Send tailored brief + book discovery call · `api_score < 0.5` → Add to quarterly nurture campaign |
| Output Schema | account_id · api_score · propensity_score · confidence_level · total_ws_potential_eur · relationship_depth · brief_text · call_plan_text · whitespace_summary · nba_actions · conflict_flag · review_notes |
| Validation | Pydantic schema-enforced — rejects malformed payloads |
| Returns To | Orchestration Agent → user response |
| LLM | None — deterministic rule lookup and schema validation |

---

## 04 Data Requirements

The data model reuses all six POC1 files and adds three POC2-specific files. Cardinality is realistic (1:1 and 1:N as appropriate).

### 04.1 Dataset Sizing

Consistent with POC1 v3:

| Dataset | Accounts | Purpose | Storage |
|---|---|---|---|
| Training | 2,500 | Reuses POC1's trained pickle — no separate training run | `data/training/` (gitignored) |
| Runtime/Demo | 50 | Live pipeline execution and show-and-tell | `data/synthetic/` (committed) |

**ID range convention:** same as POC1 — training uses `ACME-EU-00001` to `ACME-EU-02500`, runtime uses `ACME-EU-90001` to `ACME-EU-90050`. POC2 inherits the golden-path account `ACME-EU-90001`.

**POC2 does not retrain the XGBoost model.** It loads POC1's pickle and uses the same `features.py` to compute propensity scores. This is an explicit architectural choice — a single source of truth for propensity across all three POCs.

### 04.2 File Summary (POC1 reuse + POC2-specific)

| File | Origin | Cardinality | Training Rows | Runtime Rows |
|---|---|---|---|---|
| accounts.csv | POC1 reuse | 1:1 | 2,500 | 50 |
| opportunities.csv | POC1 reuse | 1:N (4/account) | 10,000 | 200 |
| snowflake_metrics.csv | POC1 reuse | 1:1 | 2,500 | 50 |
| external_funds.csv | POC1 reuse | 1:N (~60%) | ~1,500 | ~30 |
| conferences.csv | POC1 reuse | catalog | ~25 | ~25 |
| conference_attendance.csv | POC1 reuse | M:N | ~6,250 | ~125 |
| **contacts.csv** | **POC2 new** | **1:N (3–5/account)** | **~10,000** | **~200** |
| **account_product_matrix.csv** | **POC2 new** | **M:N via product_catalog** | **~20,000** | **~400** |
| **product_catalog.csv** | **POC2 new** (shared with POC3) | **catalog** | **8** | **8** |
| **Total raw rows** | | | **~53,000** | **~1,100** |

### 04.3 POC2-Specific Schemas

#### contacts.csv (1:N, 3–5 contacts per account)

| Column | Type | Notes |
|---|---|---|
| contact_id | string | PK, format `CNT-NNNNNN` |
| account_id | string | FK to accounts |
| full_name | string | Synthetic European names |
| role | enum | CEO, CFO, COO, Head of Ops, Portfolio Manager, Compliance, IT, Other |
| seniority | enum | C-Level, VP, Director, Manager, Individual Contributor |
| email | string | Synthetic, format `first.last@acmeXXXXX.example` |
| engagement_score | float | 0.0 – 1.0 (prior interaction history) |
| product_interests | string | Comma-separated product_ids the contact has engaged with |

**Distribution:** each account has exactly 3–5 contacts (uniform), at least one C-Level or VP per account. Contact role mix weighted toward Finance/Ops (60%) vs. IT/Other (40%).

#### product_catalog.csv (shared with POC3, 8 fixed products)

| Column | Type | Notes |
|---|---|---|
| product_id | string | PK, format `PROD-NN` |
| product_line | string | Fund Admin, Middle Office, ESG Reporting, AIFMD, Depositary, Tax Services, Private Client, Transfer Agency |
| asset_class_fit | string | PE, RE, Hedge, Private Client, Mixed |
| region_fit | string | Comma-separated country codes |
| typical_deal_size_eur | float | Used for expected revenue calculations |
| expansion_potential | enum | Low, Medium, High |

Same 8 products for training and runtime (catalog does not scale with dataset size).

#### account_product_matrix.csv (M:N join, every account × every product)

| Column | Type | Notes |
|---|---|---|
| account_id | string | FK |
| product_id | string | FK to product_catalog |
| has_product | bool | Current ownership |
| current_revenue_eur | float | 0.0 if `has_product=False` |
| potential_revenue_bucket | enum | Low, Medium, High (only meaningful when `has_product=False`) |
| whitespace_priority | enum | P1, P2, P3 (sales-ops assigned) |

**Cardinality:** 2,500 accounts × 8 products = 20,000 rows (training); 50 × 8 = 400 rows (runtime). Every account has a row for every product, even if `has_product=True`. This makes whitespace scoring a simple filter rather than a complex join.

**Distribution:** target ~40% `has_product=True` across the matrix. Of the remaining 60% whitespace cells, ~30% Low / ~50% Medium / ~20% High potential.

### 04.4 Engineered Demo Accounts (Runtime)

Inherited from POC1 runtime (same 50 accounts). POC2 adds these specific engineering rules:

| Group | Count | POC2-specific engineering |
|---|---|---|
| Golden path (`ACME-EU-90001`) | 1 | 5 contacts (2 C-Level), already owns 3 products, 4 high-potential whitespace cells → high propensity, high whitespace, confident Bucket A |
| Engineered conflicts | 3 | 1 high propensity + zero whitespace (owns all 8 products); 1 low propensity + 600K whitespace; 1 broken relationship_depth signal |
| Clear low-priority | 5 | 3 contacts, low engagement scores, owns 1 low-rev product, all whitespace Low potential |
| Borderline | 8 | Mixed signals — propensity around 0.5, moderate whitespace, average relationships |
| Background | 33 | Natural distribution |

---

## 05 Feature Engineering

POC2 reuses POC1's `app/features.py` for all eight propensity features. POC2 adds **four additional features** specific to account planning, computed in `app/features_poc2.py` which imports and extends POC1's module.

### 05.1 POC2 Feature Extensions

| Feature | Description | Formula |
|---|---|---|
| total_ws_potential_eur | Total whitespace revenue potential per account | `Σ expected_revenue_eur × whitespace_flag` across all 8 products |
| relationship_depth | Weighted relationship strength (0–1) | `0.4 × norm(num_contacts) + 0.3 × avg(contact.engagement_score) + 0.3 × norm(len(opportunities))` |
| contact_influence (per contact) | Contact importance for call planning | `role_weight[role] × seniority_weight[seniority] × engagement_score` |
| api_score | Account Planning Index (0–1) | `0.5 × propensity_score + 0.3 × norm(total_ws_potential_eur) + 0.2 × strategic_priority_flag` |

### 05.2 Weight Tables (locked)

```python
ROLE_WEIGHTS = {
    "CEO": 1.0, "CFO": 0.95, "COO": 0.9,
    "Head of Ops": 0.8, "Portfolio Manager": 0.75,
    "Compliance": 0.6, "IT": 0.5, "Other": 0.3,
}

SENIORITY_WEIGHTS = {
    "C-Level": 1.0, "VP": 0.85, "Director": 0.7,
    "Manager": 0.5, "Individual Contributor": 0.3,
}

EXPECTED_REVENUE_MAP = {"Low": 50_000, "Medium": 150_000, "High": 300_000}

API_SCORE_WEIGHTS = {"propensity": 0.5, "whitespace": 0.3, "strategic": 0.2}
```

All weights live in `app/constants.py` and are documented for ISO 42001 review.

---

## 06 Decision Rules

### 06.1 Conflict Detection (Validation Agent)

```python
def is_conflict(propensity: float, ws_potential_eur: float) -> tuple[bool, str]:
    if propensity >= 0.7 and ws_potential_eur < 50_000:
        return True, "High propensity but negligible whitespace — already saturated account"
    if propensity <= 0.3 and ws_potential_eur > 500_000:
        return True, "Large whitespace but low buying intent — review targeting strategy"
    return False, ""
```

### 06.2 Account Brief Agent Prompt (locked starting point)

```
You are the Account Brief Agent for IQ-EQ FAM/PIAO account planning.

Given the following structured account data:
- account_id, country, segment, fund_size_eur
- propensity_score (0-1, from XGBoost)
- total_ws_potential_eur
- relationship_depth (0-1)
- api_score (0-1)
- top 3 whitespace opportunities: [{product, expected_rev_eur}]
- top 3 contacts: [{name, role, seniority, influence_score}]

Produce a structured 1-page account brief with exactly 5 sections:
1. Summary (2-3 sentences, lead with api_score interpretation)
2. Relationship & Performance (reference relationship_depth and recent opps)
3. Whitespace & Upsell Opportunities (reference top 3 by expected_rev)
4. Key Contacts (reference top 3 by influence_score)
5. Recommended Next Actions (3 bullet points, aligned with api_score bucket)

Also produce a call_plan_text for the highest-influence contact with:
- Objectives (3 bullets)
- Suggested agenda (4 bullets)
- Key questions (3 bullets)

Constraints:
- Do NOT invent numbers. Every statistic must come from the structured input above.
- Do NOT recalculate propensity, whitespace, or api_score.
- Do NOT recommend actions outside the provided NBA rules.

Return strict JSON: {"brief_text": "...", "call_plan_text": "..."}
```

### 06.3 NBA Resolution (Formatting Agent — deterministic)

| API Score | NBA Action | Description | Due |
|---|---|---|---|
| `≥ 0.75` | qbr | Schedule Quarterly Business Review | 7 days |
| `0.5 – 0.75` | brief_plus_call | Send tailored brief + book discovery call | 14 days |
| `< 0.5` | nurture | Add to quarterly nurture campaign | 90 days |

---

## 07 Execution Flow

Linear pipeline. The Orchestration Agent initiates and receives. No hub-and-spoke back to a Planner.

1. User submits request (account list or country/segment filter) → Orchestration Agent
2. Orchestration Agent generates `pipeline_run_id`, delegates to Data Agent
3. Data Agent loads + joins all 9 CSVs → passes validated raw dataset to Whitespace Scoring Agent
4. Whitespace Scoring Agent computes `features.py` output, loads POC1 pickle, scores propensity, computes whitespace flags and api_score per account → passes to Account Brief Agent
5. Account Brief Agent invokes **OpenRouter** via the blueprint router → generates `brief_text` + `call_plan_text` per account → passes to Validation Agent
6. Validation Agent applies conflict rules → flagged accounts appended to `logs/governance_queue.jsonl` → passes all accounts to Formatting Agent
7. Formatting Agent resolves NBA by api_score bucket, validates schema via Pydantic, assembles final JSON → returns to Orchestration Agent
8. Orchestration Agent delivers final response directly to user

---

## 08 Output Schema

```json
{
  "pipeline_run_id": "uuid4",
  "generated_at": "2026-04-08T12:34:56Z",
  "model_version": "xgb_propensity_v1+router_v1+poc2_v1",
  "accounts": [
    {
      "account_id": "ACME-EU-90001",
      "api_score": 0.82,
      "propensity_score": 0.84,
      "confidence_level": 0.91,
      "total_ws_potential_eur": 750000,
      "relationship_depth": 0.78,
      "brief_text": "**Summary**\nACME-EU-90001 (DE, FAM) is a top-tier account with an API score of 0.82...\n...",
      "call_plan_text": "**Objectives**\n- Confirm ESG Reporting requirements for Q3...\n...",
      "whitespace_summary": [
        {"product": "ESG Reporting", "expected_rev_eur": 300000},
        {"product": "Middle Office", "expected_rev_eur": 300000},
        {"product": "Tax Services", "expected_rev_eur": 150000}
      ],
      "nba_actions": [
        {"action_type": "qbr", "description": "Schedule Quarterly Business Review", "due_in_days": 7}
      ],
      "conflict_flag": false,
      "review_notes": ""
    }
  ]
}
```

---

## 09 API Surface

The prototype exposes a **single endpoint**. Other endpoints from the v2 spec (`/account_brief_data`, `/call_plan_data`, `/account_view/{id}`) are not built.

| Endpoint | Method | Description |
|---|---|---|
| `/plan_accounts` | POST | Trigger full pipeline for accounts in `data/synthetic/` filtered by payload. Returns structured account planning payload. |

---

## 10 Stub Strategy

| Component | Prototype Stub |
|---|---|
| Copilot UX | Not built — JSON response only |
| Governance Workbench | Append `conflict_flag=True` accounts to `logs/governance_queue.jsonl` |
| Audit log | `logs/audit.jsonl` — one line per agent invocation |
| Override mechanism | Out of scope |
| Error handling | Fail loudly with structured exception; no retries |
| Auth / RBAC | None |
| Persistence | None — stateless per request |
| `/account_view/{id}` | Not built |
| Track Changes on briefs | Not built |

---

## 11 Project Layout

POC2 lives alongside POC1 in a shared monorepo structure:

```
poc2-account-planning/
├── app/
│   ├── main.py                  # FastAPI entry, POST /plan_accounts
│   ├── orchestration_agent.py
│   ├── agents/
│   │   ├── data_agent.py
│   │   ├── whitespace_scoring_agent.py   # loads POC1 pickle + computes ws
│   │   ├── account_brief_agent.py        # LLM via OpenRouter
│   │   ├── validation_agent.py
│   │   └── formatting_agent.py
│   ├── features.py              # imports from poc1/app/features.py
│   ├── features_poc2.py         # POC2-specific feature extensions
│   ├── data_gen_poc2.py         # POC2-specific generators (contacts, matrix)
│   ├── schemas.py               # pydantic models
│   └── constants.py             # thresholds, NBA map, weight tables
├── data/
│   ├── training/                # gitignored, extends POC1 training with POC2 files
│   └── synthetic/               # committed, 50 accounts + POC2 files
├── models/
│   └── xgb_propensity_v1.pkl    # symlinked from POC1 — single source of truth
├── scripts/
│   ├── generate_training_data_poc2.py
│   └── generate_runtime_data_poc2.py
├── logs/
├── tests/
│   ├── test_feature_parity_poc2.py
│   ├── test_api_score_bounds.py        # api_score ∈ [0, 1] for all 50 accounts
│   └── test_golden_path_poc2.py
├── .env.example                 # OPENROUTER_API_KEY, POC2_LLM_MODEL
└── README.md
```

**Critical:** `models/xgb_propensity_v1.pkl` is NOT regenerated in POC2. It is the same pickle produced by POC1's `train_xgb.py`. Ship it as a symlink or hard copy, never retrain.

---

## 12 LLM Provider: OpenRouter

POC2 standardises on **OpenRouter** as the LLM gateway. All LLM calls in the Account Brief Agent route through the multi-provider router in `agentic-ai-blueprint`, configured to use OpenRouter as the transport.

### 12.1 Why OpenRouter

- **Single API, multiple models.** Can switch between Claude, GPT-4, Gemini, Llama, etc. without code changes — only an env var update.
- **Unified billing and rate limiting** across all model providers.
- **Graceful fallback.** If one model provider is down, OpenRouter can fail over to another automatically.
- **Cost visibility.** One dashboard for all LLM spend across the three POCs.
- **Matches the `agentic-ai-blueprint` multi-provider router pattern.** No custom SDK code required.

### 12.2 Configuration

```python
# .env
OPENROUTER_API_KEY=sk-or-v1-...
POC2_LLM_MODEL=anthropic/claude-3.5-sonnet  # or openai/gpt-4o-mini, google/gemini-pro-1.5, etc.
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# app/agents/account_brief_agent.py
from blueprint.router import LLMRouter

router = LLMRouter(
    provider="openrouter",
    api_key=os.environ["OPENROUTER_API_KEY"],
    model=os.environ.get("POC2_LLM_MODEL", "anthropic/claude-3.5-sonnet"),
    base_url=os.environ["OPENROUTER_BASE_URL"],
)

response = router.complete(
    system_prompt=ACCOUNT_BRIEF_SYSTEM_PROMPT,
    user_prompt=render_account_context(account),
    response_format="json",
    temperature=0.2,  # low for factual briefs
    max_tokens=1500,
)
```

### 12.3 Model Selection Guidance

| Use case | Recommended OpenRouter model |
|---|---|
| Default (balanced cost/quality) | `anthropic/claude-3.5-sonnet` |
| Budget-conscious demo runs | `openai/gpt-4o-mini` |
| Long-context requirements | `anthropic/claude-3.5-sonnet` or `google/gemini-pro-1.5` |
| Local/offline testing | `meta-llama/llama-3.1-70b-instruct` (via OpenRouter) |

The default is configurable at runtime — no code changes, only env var updates.

### 12.4 Production Path

In Phase 2, OpenRouter calls will be replaced with the internal **IQEQ.AI** tenant for zero data leakage. The router abstraction means this is a one-file change in `agentic-ai-blueprint`, not a POC2 modification.

---

## 13 Constraints

| Constraint | Description |
|---|---|
| Single LLM agent | Only the Account Brief Agent calls an LLM. All other agents are deterministic. |
| No ML retraining | POC2 reuses POC1's XGBoost pickle — no separate training run |
| Feature parity | POC2 feature engineering MUST reuse POC1's `features.py` for the 8 propensity features |
| No invented data | LLM must not generate numbers not present in the structured input |
| Structured outputs only | All agent outputs conform to Pydantic schema — Formatting Agent enforces |
| Conflict visibility | Conflicts must always be surfaced — never silently suppressed |
| NBA is deterministic | NBA actions are rule-based lookups on `api_score` bands |
| LLM provider locked | OpenRouter is the only supported provider in this prototype |
| Data privacy | 100% synthetic data; no real client data |

---

## 14 Definition of Done

- [ ] POC2 data generators produce training (2,500 accounts) and runtime (50 accounts) datasets with all 9 files present
- [ ] `features.py` parity test passes — POC2's 8 propensity features match POC1's exactly for shared rows
- [ ] `test_api_score_bounds.py` passes — `api_score ∈ [0, 1]` for every runtime account
- [ ] `POST /plan_accounts` returns valid JSON for all 50 runtime accounts
- [ ] Golden-path account `ACME-EU-90001` produces `api_score ≥ 0.75` and NBA `qbr`
- [ ] At least 2 of the 3 engineered conflict accounts produce `conflict_flag=True`
- [ ] Brief text contains all 5 required sections for every account
- [ ] Call plan text contains Objectives, Agenda, Key Questions for every account
- [ ] `logs/audit.jsonl` contains one entry per agent per run
- [ ] `logs/governance_queue.jsonl` contains the flagged accounts
- [ ] OpenRouter integration works with at least 2 different models (swap via env var only)
- [ ] Pydantic schema validation rejects malformed payloads (one negative test)
- [ ] README documents OpenRouter setup and model swapping

---

## 15 Future Enhancements (Phase 2+)

| Enhancement | Description | Phase |
|---|---|---|
| Copilot UX Layer | Conversational interface sitting AFTER the Orchestration Agent response | Phase 2 |
| IQEQ.AI Model Swap | Replace OpenRouter with internal IQEQ.AI tenant — zero data leakage | Phase 2 |
| Production Data Bridge | Replace synthetic CSVs with live Snowflake + CRM connectors | Phase 2 |
| Track Changes on Briefs | Sales reps edit briefs in-place; diffs logged for model improvement | Phase 2 |
| Real Contact Enrichment | LinkedIn/third-party contact data enrichment | Phase 2 |
| CRM Integration | Push NBA actions directly into Salesforce/Dynamics as tasks | Phase 2 |
| Call Plan Versioning | Multiple call plan variants per contact (discovery, renewal, upsell) | Phase 2 |
| Cross-POC Orchestration | POC2 outputs feed POC3 whitespace clustering at runtime | Phase 2 |
| Autonomous QBR Booking | Agent books meetings directly via calendar integration | Phase 3 |
| Continuous Learning | Feedback loop from rep edits back into prompt tuning | Phase 3 |

---

## 16 Open Questions Parked for v2 Spec

1. Should `api_score` weights (0.5 / 0.3 / 0.2) be tunable per region or segment?
2. How should brief length scale with account size — one page always, or proportional?
3. Call plan: top 1 contact only, or multiple variants for multiple contacts?
4. Should the LLM see historical brief drafts as few-shot examples for style consistency?
5. Confidence threshold for auto-publishing briefs without human review?
6. Real-world cardinality: is 3–5 contacts per account realistic for FAM/PIAO?
7. Product catalog scope: 8 products for prototype — what is the real production catalog size?
