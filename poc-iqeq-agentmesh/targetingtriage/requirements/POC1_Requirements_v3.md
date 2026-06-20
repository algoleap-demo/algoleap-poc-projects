# AI Targeting & Triage Agent
## Agentic Rapid Prototype — Requirements v3.0

| Field | Details |
|---|---|
| Document Type | POC Requirements Specification — Rapid Prototype |
| Version | 3.0 — April 2026 |
| Status | Approved for Implementation |
| Prepared By | AI Architecture Team |
| Classification | Confidential — Internal Use Only |
| Supersedes | v2.0 (Planner Agent removed, Mesh pattern adopted) |
| Key Changes v3 | Prototype scope locked. Six-file data model with realistic 1:N and M:N cardinality. Training set sized at 2,500 accounts. Runtime/demo set at 50 accounts. Opportunities fixed at 4 per account. Conferences split into catalog + attendance. Shared `features.py` aggregation layer introduced. All thresholds, prompts, schemas, and stub strategies locked. |

---

## 01 Overview

This document defines the **rapid prototype** of the IQ-EQ Targeting & Triage Agentic AI system for Continental Europe FAM/PIAO. The prototype demonstrates an end-to-end agentic pipeline using six specialised agents — five in a linear pipeline plus one Orchestration Agent that initiates and receives. The user selects their use case directly; no Copilot UX layer in this phase.

The Orchestration Agent receives intent, delegates to the Data Agent, the pipeline flows linearly through the agent pool, and the Formatting Agent returns the final assembled payload to the Orchestration Agent which delivers it directly to the user.

**The prototype is designed to:**
- Identify high-priority accounts across Continental Europe FAM/PIAO
- Evaluate upsell potential using ML propensity scoring (XGBoost, calibrated)
- Generate prioritised recommendations with plain-English rationale via LLM
- Provide explainable, auditable AI reasoning for every account
- Highlight uncertainty and conflicts between ML and LLM signals
- Deliver all outputs directly through the Orchestration Agent to the user
- Demonstrate the full agentic flow on synthetic data with 50 engineered demo accounts

**Out of scope for this prototype:** Copilot UX, real CRM/Snowflake connectors, Governance Workbench UI, override workflow, authentication, persistence, retraining loops, multi-POC orchestration, production error handling, latency/scale targets.

---

## 02 Objectives

- Analyse account data from multiple sources — accounts, opportunities, product usage, fund activity, conference engagement
- Prioritise opportunities using ML propensity scores and LLM contextual reasoning
- Resolve Next Best Actions deterministically inside the Formatting Agent based on priority bucket
- Support human-in-the-loop decision-making with full ISO 42001 audit trail (logging only in prototype)
- Deliver all output through the single Orchestration Agent directly to the user
- Demonstrate clear separation between deterministic ML scoring, LLM contextual reasoning, and rule-based action resolution

---

## 03 Agent Definitions

The system uses **six agents total**: one Orchestration Agent that initiates and receives, plus five specialist agents in a linear pipeline. There is no separate Planner Agent — the Orchestration Agent handles planning.

### 03.1 Orchestration Agent

| Field | Detail |
|---|---|
| Responsibility | Receives user intent, generates `pipeline_run_id`, delegates to Data Agent (single outbound delegation), receives final payload from Formatting Agent, delivers response to user |
| Input | User intent + filters (country, segment, date range) |
| Output | Final structured response to user |
| Audit | Writes pipeline start/end events to `logs/audit.jsonl` |

### 03.2 Data Agent

| Field | Detail |
|---|---|
| Responsibility | Loads and joins all six CSVs from `data/synthetic/`. Validates referential integrity. First agent in the pipeline. |
| Input Filters | country · segment · date range |
| Data Sources | accounts.csv · opportunities.csv · snowflake_metrics.csv · external_funds.csv · conferences.csv · conference_attendance.csv |
| Output | Validated raw dataset (multi-table dict) — clean, no orphaned FKs |
| Returns To | Scoring Agent |

### 03.3 Scoring Agent (ML)

| Field | Detail |
|---|---|
| Responsibility | Calls shared `features.py` to aggregate raw 1:N data into per-account feature vectors. Loads pre-trained XGBoost pickle and predicts propensity scores. |
| Input | Validated raw dataset from Data Agent |
| Output Fields | `propensity_score` (float, 0–1) · `confidence_level` (float, 0–1) |
| Key Features | win_rate · avg_deal_size_eur · open_opps_count · service_penetration · engagement_score · launch_indicator · tier_1_conf_count · growth_metrics_qoq |
| Design Rationale | Deterministic ML — not LLM — for reproducible, auditable scoring at scale |
| Model | XGBoost with isotonic calibration (`CalibratedClassifierCV`) |
| Returns To | Reasoning Agent |

### 03.4 Reasoning Agent (LLM)

| Field | Detail |
|---|---|
| Responsibility | Assigns priority bucket (A / B / C) per account. Interprets contextual signals. Generates plain-English rationale. |
| Input | `propensity_score` + `confidence_level` (from Scoring Agent) plus business context: `launch_indicator`, conference signals, segment, country |
| Output Fields | `priority_bucket` (A/B/C) · `rationale_text` (string) |
| LLM Constraint | Must NOT recalculate ML scores — receives structured scores only and adds a semantic layer on top |
| LLM Provider | Multi-provider router from `agentic-ai-blueprint`; default model configurable via env var |
| Production Path | Internal IQEQ.AI tenant in production (zero data leakage) — Phase 2 |
| Returns To | Validation Agent |

### 03.5 Validation Agent

| Field | Detail |
|---|---|
| Responsibility | Detects conflicts between ML and LLM outputs. Surfaces all conflicts — never suppresses them. |
| Conflict Rules | ML High + LLM Bucket C → `conflict_flag = True` · ML Low + LLM Bucket A → `conflict_flag = True` |
| Output Fields | `conflict_flag` (bool, per account) |
| ISO 42001 Hook | `conflict_flag=True` accounts appended to `logs/governance_queue.jsonl` for review (prototype stub for Governance Workbench) |
| Returns To | Formatting Agent (pipeline does not block on conflicts in prototype) |

### 03.6 Formatting Agent

| Field | Detail |
|---|---|
| Responsibility | (1) Resolve NBA actions using deterministic rules based on `priority_bucket`. (2) Validate all required output fields. (3) Assemble strict JSON payload. (4) Return to Orchestration Agent. |
| NBA Resolution | Priority A → Call this week (5 days) · Priority B → Send targeted brief (10 days) · Priority C → Schedule quarterly check-in (90 days) |
| Output Schema | account_id · priority_bucket · ml_score · confidence_level · conflict_flag · rationale_text · nba_actions |
| Validation | Pydantic schema-enforced — rejects any payload with missing required fields or invalid types |
| Returns To | Orchestration Agent → user response |

---

## 04 Data Requirements

The data model uses **six CSV files** with realistic cardinality. Two parallel datasets share the same schema; only training data has the `won_deal` label on `opportunities.csv`.

### 04.1 Dataset Sizing

| Dataset | Accounts | Purpose | Storage |
|---|---|---|---|
| Training | 2,500 | Train the XGBoost pickle (one-shot, offline) | `data/training/` (gitignored, regenerable) |
| Runtime/Demo | 50 | Live pipeline execution and show-and-tell | `data/synthetic/` (committed) |

**ID range convention** (prevents overlap):
- Training: `ACME-EU-00001` to `ACME-EU-02500`
- Runtime:  `ACME-EU-90001` to `ACME-EU-90050`

**Why 2,500 for training:** with ~8 features, you need ~200 examples per feature for stable tree splits — 2,500 provides comfortable headroom. AUC plateaus on synthetic data around 2K–3K; going larger adds training time with no demo benefit. 2,500 also matches realistic FAM/PIAO scale in Continental Europe, making the "trained on 2,500 accounts" claim more credible than inflated numbers.

**Why 50 for runtime:** legible on screen, demo runs in under 60 seconds, allows hand-engineering of 17 hero accounts (golden path + conflicts + clear-C + borderline) while keeping 33 background accounts.

### 04.2 File Cardinality Summary

| File | Cardinality | Training Rows | Runtime Rows |
|---|---|---|---|
| accounts.csv | 1:1 master | 2,500 | 50 |
| opportunities.csv | 1:N — exactly 4 per account | 10,000 | 200 |
| snowflake_metrics.csv | 1:1 (pre-aggregated snapshot) | 2,500 | 50 |
| external_funds.csv | 1:N (~60% of accounts have any) | ~1,500 | ~30 |
| conferences.csv | catalog (independent of accounts) | ~25 | ~25 |
| conference_attendance.csv | M:N join (~2.5 per account) | ~6,250 | ~125 |
| **Total raw rows** | | **~22,775** | **~480** |

### 04.3 Schemas

#### accounts.csv (1:1 master)

| Column | Type | Notes |
|---|---|---|
| account_id | string | PK, format `ACME-EU-NNNNN` |
| country | enum | DE, FR, IT, ES, NL, BE, CH, LU |
| segment | enum | FAM, PIAO |
| fund_size_eur | float | 1M – 5B |
| strategic_priority_flag | bool | ~15% True |

#### opportunities.csv (1:N, exactly 4 per account)

| Column | Type | Notes |
|---|---|---|
| opportunity_id | string | PK, format `OPP-NNNNNNN` |
| account_id | string | FK to accounts |
| deal_size_eur | float | 50K – 2M |
| open_date | date | ISO 8601 |
| close_date | date | ISO 8601, nullable if `status=open` |
| status | enum | won, lost, open |
| won_deal | bool | **Training only.** Derived: `status == 'won'`. Target ~35% positive class. |

#### snowflake_metrics.csv (1:1, pre-aggregated)

| Column | Type | Notes |
|---|---|---|
| account_id | string | FK |
| service_penetration | float | 0.0 – 1.0 |
| engagement_score | float | 0.0 – 100.0 |
| growth_metrics_qoq | float | -0.5 – +1.5 |

#### external_funds.csv (1:N, ~60% coverage)

| Column | Type | Notes |
|---|---|---|
| fund_record_id | string | PK |
| account_id | string | FK |
| launch_date | date | ISO 8601 |
| launch_size_eur | float | nullable |

*Note: splitting funds into a catalog + relationships table is a v2 cleanup, parked as out-of-scope for this prototype.*

#### conferences.csv (catalog — same ~25 for both datasets)

| Column | Type | Notes |
|---|---|---|
| conference_id | string | PK, format `CONF-NNN` |
| conference_name | string | e.g., "ALFI Private Assets 2026" |
| conference_date | date | ISO 8601 |
| location | string | City |
| tier | enum | tier_1, tier_2, tier_3 (proxy for prestige) |

The catalog is the same set of conferences for both training and runtime — conferences are real-world entities that exist independently of which accounts you happen to have in your dataset. This enables features like "did the account attend a tier-1 conference."

#### conference_attendance.csv (M:N join)

| Column | Type | Notes |
|---|---|---|
| account_id | string | FK to accounts |
| conference_id | string | FK to conferences |
| signal_strength | enum | low, medium, high (per-attendance — e.g., spoke vs. attended) |

**Distribution:** ~30% of accounts attend 0 conferences, ~40% attend 1–2, ~25% attend 3–6, ~5% are regulars with 7+. Average ~2.5 per account.

### 04.4 Engineered Demo Accounts (Runtime, 50 total)

Every "interesting" account in the demo maps to a named `account_id`. Hand-engineering 17 of 50 accounts gives full coverage for any audience question.

| Group | Count | Purpose |
|---|---|---|
| Golden path (`ACME-EU-90001`) | 1 | 4 won opportunities, attends 5 tier-1 conferences, 2 recent fund launches → confidently Bucket A. The account walked through end-to-end in the demo narrative. |
| Engineered conflicts | 3 | High ML predictors but zero conferences and zero fund signals (or vice versa) — forces `conflict_flag=True` and demonstrates the Validation Agent. |
| Clear Bucket C | 5 | 4 opportunities all lost, no conferences, no funds → trivially Bucket C. Proves the model isn't just labelling everything as A. |
| Borderline | 8 | Mixed signals near decision boundaries — exercises `rationale_text` quality. |
| Background | 33 | Naturally distributed across A/B/C — makes the dataset feel real. |
| **Total** | **50** | |

---

## 05 Feature Engineering

`app/features.py` is the **single source of truth** that converts raw 1:N data into the per-account feature matrix that XGBoost consumes. It runs identically at training time and runtime, eliminating the most common ML pipeline bug: training/serving skew.

### 05.1 Aggregation Function

```python
def compute_features(account_id: str, raw: dict) -> dict:
    opps    = raw["opportunities"][raw["opportunities"].account_id == account_id]
    funds   = raw["external_funds"][raw["external_funds"].account_id == account_id]
    attend  = raw["conference_attendance"][raw["conference_attendance"].account_id == account_id]
    confs   = raw["conferences"]  # catalog
    metrics = raw["snowflake_metrics"][raw["snowflake_metrics"].account_id == account_id].iloc[0]

    closed = opps[opps.status.isin(["won", "lost"])]
    attended_confs = confs[confs.conference_id.isin(attend.conference_id)]

    return {
        "win_rate":            (closed.status == "won").sum() / max(len(closed), 1),
        "avg_deal_size_eur":   opps.deal_size_eur.mean() if len(opps) else 0.0,
        "open_opps_count":     (opps.status == "open").sum(),
        "service_penetration": metrics.service_penetration,
        "engagement_score":    metrics.engagement_score
                               + 5 * len(attend)
                               + 10 * (attend.signal_strength == "high").sum(),
        "launch_indicator":    int((funds.launch_date >= cutoff_90d).any()),
        "tier_1_conf_count":   (attended_confs.tier == "tier_1").sum(),
        "growth_metrics_qoq":  metrics.growth_metrics_qoq,
    }
```

**Output:** one row per account → 2,500 rows (training) or 50 rows (runtime), 8 columns. This is the matrix XGBoost trains and predicts on.

### 05.2 Feature Catalog

| Feature | Description | Source Tables |
|---|---|---|
| win_rate | Wins / closed opportunities | opportunities |
| avg_deal_size_eur | Mean deal size across all opportunities | opportunities |
| open_opps_count | Number of currently open opportunities | opportunities |
| service_penetration | Service adoption depth (0–1) | snowflake_metrics |
| engagement_score | Composite of usage + conference attendance | snowflake_metrics + conference_attendance |
| launch_indicator | Recent fund launch in last 90 days | external_funds |
| tier_1_conf_count | Number of tier-1 conferences attended | conference_attendance + conferences |
| growth_metrics_qoq | Period-over-period revenue growth | snowflake_metrics |

---

## 06 Model Training

### 06.1 Training Process

**Script:** `scripts/train_xgb.py` — one-shot, run once, commit the resulting pickle.

**Hidden true label function** — used by `generate_training_data.py` to assign `status` per opportunity. The Scoring Agent never sees this; it learns the pattern from the aggregated features:

```python
true_prob = sigmoid(
      1.5 * account.service_penetration
    + 1.0 * (account.engagement_score / 100)
    + 0.8 * account.has_recent_fund_launch
    + 0.6 * account.tier_1_conf_count_normalized
    + 0.5 * account.strategic_priority_flag
    - 1.0   # bias to keep ~35% won across all opps
)
opp_status = "won" if np.random.binomial(1, true_prob) else "lost"
```

Note that `win_rate` is **not** in the label function — it would be circular, since `win_rate` is itself derived from these labels. The model has to learn that `win_rate` is a strong predictor on its own.

### 06.2 Train/Test Split

70 / 15 / 15 stratified on the aggregated account label (`account_won_majority` = `win_rate >= 0.5`), fixed seed `42`. Yields ~1,750 train / ~375 val / ~375 test accounts.

### 06.3 XGBoost Configuration

```python
XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric="logloss",
)
```

Wrap with `CalibratedClassifierCV(method="isotonic", cv=3)` — XGBoost outputs are over-confident at extremes and the conflict-detection threshold rule depends on calibrated probabilities.

### 06.4 Acceptance Metrics

- AUC on test set ≥ 0.75 (synthetic data ceiling around 0.85)
- Confusion matrix at 0.5 threshold
- Score distribution histogram saved to `models/score_distribution.png`

After training, inspect the histogram on the runtime 50 before locking `ML_HIGH_THRESHOLD`. The provisional value of 0.70 may need to shift based on observed score distribution.

### 06.5 Pickle Contents

```python
joblib.dump({
    "model": calibrated_model,
    "feature_names": FEATURE_ORDER,
    "model_version": "xgb_propensity_v1",
    "trained_at": "2026-04-08T...",
    "test_auc": 0.82,
    "training_account_count": 2500,
}, "models/xgb_propensity_v1.pkl")
```

The Scoring Agent loads the pickle, asserts `df.columns.tolist() == feature_names`, and fails loudly on mismatch.

---

## 07 Decision Rules

### 07.1 Conflict Detection (Validation Agent)

```python
ML_HIGH_THRESHOLD = 0.70   # provisional, may be re-tuned post-training
ML_LOW_THRESHOLD  = 0.30

LLM_BUCKET_TO_LEVEL = {"A": "High", "B": "Medium", "C": "Low"}

def is_conflict(ml_score: float, llm_bucket: str) -> bool:
    ml_level = ("High" if ml_score >= ML_HIGH_THRESHOLD
                else "Low" if ml_score <= ML_LOW_THRESHOLD
                else "Medium")
    llm_level = LLM_BUCKET_TO_LEVEL[llm_bucket]
    return (ml_level, llm_level) in {("High", "Low"), ("Low", "High")}
```

`confidence_level` flows through the pipeline unused in v1 — reserved for v2 use as a tiebreaker or low-confidence flag.

### 07.2 Reasoning Agent Prompt (locked starting point)

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

### 07.3 NBA Resolution (Formatting Agent — deterministic)

| Bucket | NBA Action | Description | Due |
|---|---|---|---|
| A | call | Call this week | 5 days |
| B | send_link | Send targeted product brief | 10 days |
| C | schedule | Schedule quarterly check-in | 90 days |

NBA actions are rule-based lookups, not LLM inferences — ensuring full auditability under ISO 42001.

### 07.4 Decision Layer Summary

| Layer | Role | Constraint |
|---|---|---|
| ML (Scoring Agent) | Statistical propensity score from historical patterns | Does NOT incorporate contextual signals — deterministic and reproducible |
| LLM (Reasoning Agent) | Contextual reasoning, assigns human-readable priority bucket | Does NOT recalculate ML scores — adds semantic layer only |
| NBA (Formatting Agent) | Deterministic rule lookup based on `priority_bucket` | Auditable for ISO 42001 — every NBA traceable to a rule |
| Conflict Handling | ML High + LLM Low (or vice versa) → `conflict_flag=True` | Both scores preserved; flagged accounts logged to governance queue |

---

## 08 Execution Flow

Linear pipeline. The Orchestration Agent initiates and receives. Agents pass results to the next agent in sequence — no hub-and-spoke back to a Planner.

1. User selects Targeting & Triage use case → intent sent to Orchestration Agent
2. Orchestration Agent generates `pipeline_run_id`, plans sequence, delegates to Data Agent (single outbound delegation)
3. Data Agent loads + joins all 6 CSVs → passes validated raw dataset to Scoring Agent
4. Scoring Agent calls `features.py` to aggregate raw data into per-account feature matrix → loads XGBoost pickle → emits `propensity_score` + `confidence_level` per account → passes to Reasoning Agent
5. Reasoning Agent invokes LLM router with prompt + scores + context → emits `priority_bucket` + `rationale_text` per account → passes to Validation Agent
6. Validation Agent applies conflict rule → flags accounts where ML and LLM disagree → appends flagged accounts to `logs/governance_queue.jsonl` → passes all accounts (flagged and unflagged) to Formatting Agent
7. Formatting Agent resolves NBA per bucket, validates schema via pydantic, assembles final JSON → returns payload to Orchestration Agent
8. Orchestration Agent delivers final response directly to user

---

## 09 Output Schema

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

| Field | Type | Description |
|---|---|---|
| pipeline_run_id | UUID | Unique per pipeline invocation, threaded through audit log |
| generated_at | ISO timestamp | When the response was assembled |
| model_version | string | Combined XGBoost + LLM router version |
| account_id | string | Unique account identifier |
| priority_bucket | enum | A / B / C |
| ml_score | float | XGBoost propensity score (0–1, calibrated) |
| confidence_level | float | Model confidence indicator (0–1) — reserved for v2 use |
| conflict_flag | bool | True if ML and LLM signals conflict |
| rationale_text | string | LLM-generated plain-English explanation |
| nba_actions | array | NBA resolved by Formatting Agent — single element in v1, array shape preserved for v2 extensibility |

---

## 10 API Surface

The prototype exposes a **single endpoint**. Other endpoints from the v2 spec (`GET /account_view/{id}`, `POST /prioritize_accounts`) are not built in this phase.

| Endpoint | Method | Description |
|---|---|---|
| `/score_accounts` | POST | Trigger full pipeline for all accounts in `data/synthetic/`. Returns the structured prioritisation payload defined in Section 09. |

---

## 11 Stub Strategy

| Component | Prototype Stub |
|---|---|
| Governance Workbench | Append `conflict_flag=True` accounts to `logs/governance_queue.jsonl`. Pipeline does NOT block on conflicts. |
| Audit log | `logs/audit.jsonl` — one line per agent invocation: `{run_id, agent, input_hash, output_hash, ts, duration_ms}` |
| Override mechanism | Out of scope |
| Error handling | Fail loudly with structured exception; no retries |
| Auth / RBAC | None |
| Persistence | None — stateless per request |
| `GET /account_view/{id}` | Not built |
| `POST /prioritize_accounts` | Not built |

---

## 12 Project Layout

```
poc1-targeting-triage/
├── app/
│   ├── main.py                  # FastAPI entry, POST /score_accounts
│   ├── orchestration_agent.py   # generates run_id, drives pipeline
│   ├── agents/
│   │   ├── data_agent.py        # loads + joins all 6 CSVs
│   │   ├── scoring_agent.py     # loads pickle, asserts feature order
│   │   ├── reasoning_agent.py   # uses blueprint LLM router
│   │   ├── validation_agent.py  # conflict rule
│   │   └── formatting_agent.py  # NBA + pydantic schema validation
│   ├── features.py              # ⭐ SHARED aggregation: 1:N raw → 1:1 feature row
│   ├── data_gen.py              # ⭐ SHARED generators for accounts/opps/funds/attendance
│   ├── schemas.py               # pydantic models for all I/O
│   └── constants.py             # thresholds, NBA map, FEATURE_ORDER
├── data/
│   ├── training/                # gitignored, 2,500 accounts + 1:N tables, with won_deal
│   │   ├── accounts.csv
│   │   ├── opportunities.csv
│   │   ├── snowflake_metrics.csv
│   │   ├── external_funds.csv
│   │   ├── conferences.csv
│   │   └── conference_attendance.csv
│   └── synthetic/               # committed, 50 accounts + 1:N tables, no labels
│       └── (same 6 files)
├── models/
│   ├── xgb_propensity_v1.pkl    # committed
│   └── score_distribution.png   # committed sanity-check artifact
├── scripts/
│   ├── generate_training_data.py   # 2,500 accounts, seed 42, with labels
│   ├── generate_runtime_data.py    # 50 accounts, seed 43, no labels, conflicts + golden
│   └── train_xgb.py                # one-shot
├── logs/                        # audit.jsonl, governance_queue.jsonl
├── tests/
│   ├── test_feature_parity.py   # ⭐ asserts features.py is deterministic
│   └── test_golden_path.py      # ACME-EU-90001 end-to-end
├── .gitignore                   # data/training/
└── README.md
```

`features.py` and `data_gen.py` being shared between training and runtime is the structural backbone that prevents training/serving skew — the most common ML prototype bug.

---

## 13 Constraints

| Constraint | Description |
|---|---|
| No ML recalculation in LLM | Reasoning Agent must not recalculate or override ML scores |
| No unsupported fields | Agents must not generate fields not defined in the output schema |
| Structured outputs only | All agent outputs must conform to the defined Pydantic schema — Formatting Agent enforces |
| Conflict visibility | Conflicts must always be surfaced — never silently suppressed |
| NBA is deterministic | NBA actions are rule-based lookups in the Formatting Agent — not LLM inferences |
| Data privacy | No real client data in prototype — 100% synthetic. Production uses firewall-protected connectors. |
| Feature parity | Training and runtime feature engineering MUST use the same `features.py` module |
| Reproducibility | Fixed seeds (42 training, 43 runtime) — pickle and runtime data must be regenerable from scratch |

---

## 14 Definition of Done

- [ ] `scripts/train_xgb.py` produces a calibrated pickle with test AUC ≥ 0.75
- [ ] `models/score_distribution.png` is sane (not all clustered at 0 or 1)
- [ ] `ML_HIGH_THRESHOLD` re-tuned if needed after inspecting runtime score distribution
- [ ] `test_feature_parity.py` passes — `features.py` is deterministic across runs
- [ ] Feature aggregation produces exactly 2,500 rows from training data and 50 rows from runtime data, with zero orphans or duplicates
- [ ] `POST /score_accounts` returns valid JSON for all 50 runtime accounts
- [ ] At least 2 of the 3 engineered conflict accounts produce `conflict_flag=True`
- [ ] Golden-path account `ACME-EU-90001` returns Bucket A with a coherent rationale
- [ ] `logs/audit.jsonl` contains one entry per agent per run
- [ ] `logs/governance_queue.jsonl` contains the flagged accounts
- [ ] Pydantic schema validation rejects malformed payloads (one negative test)
- [ ] README has a one-command run instruction and a demo walkthrough script

---

## 15 Future Enhancements (Phase 2+)

| Enhancement | Description | Phase |
|---|---|---|
| Production Data Bridge | Replace synthetic CSVs with live Snowflake views and CRM (Salesforce/Dynamics) connectors | Phase 2 |
| IQEQ.AI Model Swap | Replace external LLM API calls with internal firewall-protected IQEQ.AI tenant — zero data leakage | Phase 2 |
| Copilot UX Layer | Conversational interface on top of the Response to User output, enabling natural-language follow-up queries. Sits AFTER the Orchestration Agent response — not between user and orchestrator. | Phase 2 |
| CRM Integration | Embed Governance Workbench and NBA actions directly into CRM as a native panel | Phase 2 |
| Governance Workbench UI | Replace JSONL stub with a real review interface, override workflow, and write-back semantics | Phase 2 |
| Funds Catalog Split | Split `external_funds.csv` into `funds.csv` catalog + `account_fund_relationships.csv` join table | Phase 2 |
| Confidence-Level Usage | Wire `confidence_level` into the conflict rule as a tiebreaker | Phase 2 |
| Whitespace Orchestration | Connect Whitespace Agent (POC 3) directly to the Orchestration Agent for real-time gap monitoring | Phase 2 |
| Autonomous NBA Execution | Agents trigger NBA actions (send email, book meeting, push CRM task) without per-action human initiation | Phase 3 |
| Continuous Learning | Model retraining pipeline on human override feedback and closed-deal outcome data | Phase 3 |
| Multi-POC Orchestration | Cross-POC agent collaboration — Targeting, Account Planning, and Whitespace as a unified intelligence pipeline | Phase 3 |

---

## 16 Open Questions Parked for v2 Spec

These questions are not blocking the prototype but should be answered before production planning:

1. How should `confidence_level` drive decisions (tiebreaker, low-confidence flag, both)?
2. Sync vs. async Governance Workbench review loop — does the pipeline wait for human approval, or fire-and-forget?
3. Override category taxonomy and write-back semantics — does an override mutate the payload, append to a log, or retrigger the pipeline?
4. Which fields are PII-sensitive when real connectors land?
5. Is the "Mesh" pattern actually wanted for production, or is the linear pipeline the production target?
6. Real-world cardinality assumptions: is 4 opportunities per account realistic for FAM/PIAO? Is ~60% fund coverage right? Is ~2.5 conferences per account right?
7. Confidence target for test AUC — is 0.75 acceptable, or do we want 0.80+?
8. Account-level vs. opportunity-level prediction — does the business want per-account prioritisation (current design) or per-deal scoring?
