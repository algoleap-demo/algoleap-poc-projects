# POC1 — Targeting & Triage Agent
## Rapid Prototype Scope Contract (v1)

**Owner:** Prasanna · **Stack:** Python 3.11+ / FastAPI · **LLM:** Multi-provider router (agentic-ai-blueprint) · **Training set:** 2,500 labelled synthetic accounts · **Runtime set:** 50 synthetic accounts · **Timebox:** rapid prototype

---

## 1. Locked decisions

| Area | Decision |
|---|---|
| Pipeline shape | Linear: Orchestration → Data → Scoring → Reasoning → Validation → Formatting → Orchestration → User |
| Agent count | 6 total (5 specialist + 1 Orchestration). Use this number everywhere. |
| LLM provider | Multi-provider router from `agentic-ai-blueprint`; default model configurable via env var |
| ML scorer | Pre-trained XGBoost pickle (`models/xgb_propensity_v1.pkl`), trained offline on 2,500 labelled synthetic accounts (~10K opportunity rows after 1:N expansion) |
| Training data | 2,500 accounts with multi-table 1:N relationships, regenerable via script (gitignored), seed `42` |
| Runtime data | 50 accounts, no labels, committed to repo, seed `43`, includes engineered conflicts + golden path |
| Feature engineering | **Single source of truth** in `app/features.py` — aggregates raw 1:N tables into a single feature row per account; used by both training and runtime |
| API surface | One endpoint only: `POST /score_accounts` |
| Persistence | None — in-memory + JSONL log files |
| Auth | None for prototype |

---

## 2. CSV schemas (locked)

The data model uses **six files** with realistic cardinality. The label `won_deal` lives at the **opportunity level** (one label per deal), and is aggregated to account level by `features.py` before training.

- **Training:** `data/training/` — 2,500 accounts, gitignored, regenerated via `scripts/generate_training_data.py`, seed `42`
- **Runtime:** `data/synthetic/` — 50 accounts, committed, regenerated via `scripts/generate_runtime_data.py`, seed `43`

Both generators call the **same underlying functions** in `app/data_gen.py` to guarantee distribution parity. Only seed and row counts differ.

**ID range convention** (prevents accidental overlap between train/runtime):
- Training: `ACME-EU-00001` to `ACME-EU-02500`
- Runtime:  `ACME-EU-90001` to `ACME-EU-90050`

### File summary

| File | Cardinality | Training rows | Runtime rows |
|---|---|---|---|
| accounts.csv | 1:1 master | 2,500 | 50 |
| opportunities.csv | 1:N (exactly 4 per account) | 10,000 | 200 |
| snowflake_metrics.csv | 1:1 (pre-aggregated snapshot) | 2,500 | 50 |
| external_funds.csv | 1:N (~60% of accounts have any) | ~1,500 | ~30 |
| conferences.csv | catalog (independent of accounts) | ~25 | ~25 |
| conference_attendance.csv | M:N join (~2.5 per account) | ~6,250 | ~125 |
| **Total raw rows** | | **~22,775** | **~480** |

### accounts.csv (1:1)
| Column | Type | Notes |
|---|---|---|
| account_id | string | PK, format `ACME-EU-NNNNN` |
| country | enum | DE, FR, IT, ES, NL, BE, CH, LU |
| segment | enum | FAM, PIAO |
| fund_size_eur | float | 1M – 5B |
| strategic_priority_flag | bool | ~15% True |

### opportunities.csv (1:N — exactly 4 per account)
| Column | Type | Notes |
|---|---|---|
| opportunity_id | string | PK, format `OPP-NNNNNNN` |
| account_id | string | FK to accounts |
| deal_size_eur | float | 50K – 2M |
| open_date | date | ISO 8601 |
| close_date | date | ISO 8601, nullable if `status=open` |
| status | enum | won, lost, open |
| **won_deal** | **bool** | **Training only — label per opportunity. ~35% positive class.** Derived: `status == 'won'`. |

### snowflake_metrics.csv (1:1, pre-aggregated)
| Column | Type | Notes |
|---|---|---|
| account_id | string | FK |
| service_penetration | float | 0.0 – 1.0 |
| engagement_score | float | 0.0 – 100.0 |
| growth_metrics_qoq | float | -0.5 – +1.5 |

### external_funds.csv (1:N, ~60% coverage)
| Column | Type | Notes |
|---|---|---|
| fund_record_id | string | PK |
| account_id | string | FK |
| launch_date | date | ISO 8601 |
| launch_size_eur | float | nullable |

*Note: split into a separate funds catalog + relationships table is a v2 cleanup. Out of scope for prototype.*

### conferences.csv (catalog — ~25 distinct conferences)
| Column | Type | Notes |
|---|---|---|
| conference_id | string | PK, format `CONF-NNN` |
| conference_name | string | e.g., "ALFI Private Assets 2026" |
| conference_date | date | ISO 8601 |
| location | string | City |
| tier | enum | tier_1, tier_2, tier_3 (proxy for prestige) |

The catalog is the **same ~25 conferences** for both training and runtime — conferences are real-world entities that exist independently of which accounts you happen to have in your dataset.

### conference_attendance.csv (M:N join)
| Column | Type | Notes |
|---|---|---|
| account_id | string | FK to accounts |
| conference_id | string | FK to conferences |
| signal_strength | enum | low, medium, high (per attendance — e.g., spoke vs. attended) |

**Distribution:** ~30% of accounts attend 0 conferences, ~40% attend 1–2, ~25% attend 3–6, ~5% are regulars with 7+. Average ~2.5 per account.

---

## 2a. Feature aggregation (locked)

`app/features.py` is the single function that converts raw 1:N data into the per-account feature matrix that XGBoost consumes. It runs identically at training time and runtime.

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

**Why this is the structural backbone of the prototype:** training/serving skew is the #1 silent failure mode in ML pipelines. Sharing this function between training and runtime — and testing it via `test_feature_parity.py` — eliminates that risk entirely.

### Engineered demo accounts (runtime, 50 accounts total)

| Group | Count | Purpose |
|---|---|---|
| Golden path (`ACME-EU-90001`) | 1 | 4 opps (4 won), attends 5 tier-1 conferences, 2 recent fund launches → confidently Bucket A |
| Engineered conflicts | 3 | e.g., 4 won opps but zero conferences/funds (high ML, low LLM context) — forces `conflict_flag=True` |
| Clear Bucket C | 5 | 4 opps all lost, no conferences, no funds — trivial Bucket C |
| Borderline | 8 | Mixed signals near decision boundaries — exercises rationale_text |
| Background | 33 | Naturally distributed — makes the dataset feel real |
| **Total** | **50** | |

Every "interesting" account in the demo should map to a named `account_id`. Hand-engineering 17 of 50 gives you full coverage for any audience question.



---

## 3. Numeric thresholds (locked)

```python
# constants.py
ML_HIGH_THRESHOLD = 0.70
ML_LOW_THRESHOLD  = 0.30

LLM_BUCKET_TO_LEVEL = {"A": "High", "B": "Medium", "C": "Low"}

# Conflict rule
def is_conflict(ml_score: float, llm_bucket: str) -> bool:
    ml_level = "High" if ml_score >= ML_HIGH_THRESHOLD else \
               "Low"  if ml_score <= ML_LOW_THRESHOLD  else "Medium"
    llm_level = LLM_BUCKET_TO_LEVEL[llm_bucket]
    return (ml_level, llm_level) in {("High", "Low"), ("Low", "High")}
```

`confidence_level` flows through unused in v1 (Scoring Agent emits it; Formatting Agent includes it in payload). Documented as "reserved for v2."

---

## 4. Model training (locked)

**Script:** `scripts/train_xgb.py` — one-shot, run once, commit the resulting pickle.

**Training data:** 2,500 accounts (~10,000 opportunity rows + 6,250 attendance rows + 1,500 fund rows) from `data/training/`, generated with seed `42`. After `features.py` aggregation, XGBoost sees a **2,500 × 8 feature matrix**.

**Why 2,500 and not 10,000:** with 8 features, you need ~200 examples per feature for stable tree splits — that's 1,600 minimum, 2,500 is comfortable headroom. On synthetic data, AUC plateaus around 2K–3K rows; going to 10K just slows training with no demo benefit. 2,500 also matches realistic FAM/PIAO scale, which makes the "trained on 2,500 accounts" claim more credible than "10,000."

**Hidden true label function** (used by `generate_training_data.py` to assign `status` per opportunity):

```python
# Per-opportunity win probability, derived from the parent account's signals
true_prob = sigmoid(
      1.5 * account.service_penetration
    + 1.0 * (account.engagement_score / 100)
    + 0.8 * account.has_recent_fund_launch
    + 0.6 * account.tier_1_conf_count_normalized
    + 0.5 * account.strategic_priority_flag
    - 1.0   # bias to keep ~35% won across all opps
)
opp_status = "won" if np.random.binomial(1, true_prob) else "lost"
# (a fraction of opps are forced to status="open" — these have no label)
```

The label rule lives only here. The Scoring Agent never sees it — it learns the pattern from `features.py`'s aggregated output, exactly as a real model would. Note that `win_rate` (the strongest predictor) is *not* in the label function — it would be circular, since `win_rate` is itself derived from these labels. The model has to learn that win_rate is a good predictor on its own.

**Train/val/test split:** 70 / 15 / 15 stratified on the aggregated account label (`account_won_majority` = `win_rate >= 0.5`), fixed seed. Yields ~1,750 train / ~375 val / ~375 test accounts.

**XGBoost params (starting point):**
```python
XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric="logloss",
    # scale_pos_weight only if positive class drifts below 25%
)
```

**Calibration:** wrap with `CalibratedClassifierCV(method="isotonic", cv=3)`. XGBoost outputs are over-confident at extremes, and your `ML_HIGH_THRESHOLD = 0.70` rule depends on calibrated probabilities to fire correctly.

**Acceptance metrics (printed by `train_xgb.py`):**
- AUC on test set ≥ 0.75 (synthetic data, easy ceiling around 0.85)
- Confusion matrix at 0.5 threshold
- Score distribution histogram saved to `models/score_distribution.png`

**After training, inspect the histogram on the runtime 50 before locking `ML_HIGH_THRESHOLD`.** If most scores cluster between 0.4–0.6, lower the threshold; the value `0.70` in Section 3 is provisional until calibration is verified.

**Pickle contents:**
```python
joblib.dump({
    "model": calibrated_model,
    "feature_names": FEATURE_ORDER,   # exact column order
    "model_version": "xgb_propensity_v1",
    "trained_at": "2026-04-08T...",
    "test_auc": 0.82,
    "training_account_count": 2500,
}, "models/xgb_propensity_v1.pkl")
```

**Runtime contract:** Scoring Agent loads the pickle, asserts `df.columns.tolist() == feature_names`, and fails loudly on mismatch. This is the single most likely place to introduce a silent bug.

---

## 4b. Reasoning Agent prompt (sketch)

```
You are the Reasoning Agent for IQ-EQ FAM/PIAO account triage.

Given an account with:
- propensity_score: {ml_score} (0-1, from XGBoost)
- confidence_level: {confidence}
- launch_indicator: {launch}
- conference_signal: {signal_strength}
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

No threshold guardrails on the LLM in v1 — let it judge, surface conflicts via the Validation Agent.

---

## 5. Output JSON (locked)

```json
{
  "pipeline_run_id": "uuid4",
  "generated_at": "2026-04-08T12:34:56Z",
  "model_version": "xgb_v1+router_v1",
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

NBA mapping (deterministic, in Formatting Agent):
- A → `{call, "Call this week", 5}`
- B → `{send_link, "Send targeted product brief", 10}`
- C → `{schedule, "Schedule quarterly check-in", 90}`

Single-element array always in v1. Shape is array so v2 can extend.

---

## 6. Stub strategy (deferred to v2)

| Component | v1 stub |
|---|---|
| Governance Workbench | Append `conflict_flag=True` accounts to `logs/governance_queue.jsonl`. Pipeline does NOT block — flagged accounts still flow to Formatting Agent with the flag set. |
| Audit log | `logs/audit.jsonl` — one line per agent invocation: `{run_id, agent, input_hash, output_hash, ts, duration_ms}` |
| Override mechanism | Out of scope for v1 |
| Error handling | Fail loudly with structured exception; no retries |
| Auth / RBAC | None |
| Persistence | None; stateless per request |
| `GET /account_view/{id}` endpoint | Not built |
| `POST /prioritize_accounts` endpoint | Not built |

---

## 7. Project layout

```
poc1-targeting-triage/
├── app/
│   ├── main.py                  # FastAPI entry, POST /score_accounts
│   ├── orchestration_agent.py   # generates run_id, drives pipeline
│   ├── agents/
│   │   ├── data_agent.py        # loads + joins all 6 CSVs
│   │   ├── scoring_agent.py     # loads pickle, asserts feature order
│   │   ├── reasoning_agent.py   # uses blueprint router
│   │   ├── validation_agent.py  # conflict rule
│   │   └── formatting_agent.py  # NBA + schema validation (pydantic)
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
│   └── score_distribution.png   # committed, sanity-check artifact
├── scripts/
│   ├── generate_training_data.py   # 2,500 accounts, seed 42, with labels
│   ├── generate_runtime_data.py    # 50 accounts, seed 43, no labels, conflicts + golden
│   └── train_xgb.py                # one-shot, run once
├── logs/                        # audit.jsonl, governance_queue.jsonl
├── tests/
│   ├── test_feature_parity.py   # ⭐ asserts shared features.py is deterministic
│   └── test_golden_path.py      # ACME-EU-90001 end-to-end
├── .gitignore                   # data/training/
└── README.md
```

**Two files marked ⭐ are the prototype's structural backbone.** `features.py` and `data_gen.py` being shared between training and runtime is what prevents the most common ML prototype bug: training/serving skew.

---

## 8. Definition of Done (prototype)

- [ ] `scripts/train_xgb.py` produces a calibrated pickle with test AUC ≥ 0.75
- [ ] `models/score_distribution.png` is sane (not all clustered at 0 or 1)
- [ ] `ML_HIGH_THRESHOLD` re-tuned if needed after inspecting the runtime score distribution
- [ ] `test_feature_parity.py` passes — `features.py` is deterministic and produces identical output across runs
- [ ] Feature aggregation produces exactly 2,500 rows from training data and 50 rows from runtime data, with zero orphans or duplicates
- [ ] `POST /score_accounts` returns valid JSON for all 50 runtime accounts
- [ ] At least 2 of the 3 engineered conflict accounts produce `conflict_flag=True`
- [ ] Golden-path account `ACME-EU-90001` returns Bucket A with a coherent rationale
- [ ] `logs/audit.jsonl` contains one entry per agent per run
- [ ] `logs/governance_queue.jsonl` contains the flagged accounts
- [ ] Pydantic schema validation rejects malformed payloads (one negative test)
- [ ] README has a one-command run instruction and a demo walkthrough script

---

## 9. Explicitly out of scope (say this in the demo)

Governance UI · Override workflow · Real Snowflake/CRM connectors · IQEQ.AI internal LLM tenant · Copilot UX · Auth · Persistence · Retraining loop · Multi-POC orchestration · Production error handling · Latency/scale targets

---

## 10. Open questions parked for v2 spec (not blocking the prototype)

1. How does `confidence_level` drive decisions?
2. Sync vs. async Governance Workbench review loop
3. Override category taxonomy and write-back semantics
4. Which fields are PII-sensitive when real connectors land
5. Is "Mesh" pattern actually wanted, or is linear pipeline the production target?
