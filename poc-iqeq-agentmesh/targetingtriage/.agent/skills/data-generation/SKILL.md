---
name: data-generation
description: How to generate and validate synthetic training and runtime datasets for POC1 Targeting & Triage
---

# Data Generation Skill

This skill documents how to generate, regenerate, and validate the synthetic datasets that power the POC1 Targeting & Triage pipeline.

## Overview

The data model uses **6 CSV files** with realistic cardinality. Two parallel datasets share the same schema:
- **Training set** (2,500 accounts) — used offline to train the XGBoost model
- **Runtime set** (50 accounts) — used for live pipeline execution and demos

Both generators call the **same underlying functions** in `app/data_gen.py` to guarantee distribution parity. Only seed and row counts differ.

## Dataset Details

### Training Data
- **Location:** `data/training/`
- **Script:** `scripts/generate_training_data.py`
- **Seed:** `42`
- **Accounts:** 2,500 (IDs: `ACME-EU-00001` to `ACME-EU-02500`)
- **Status:** gitignored, regenerable from scratch
- **Special:** includes `won_deal` label on opportunities.csv

### Runtime Data
- **Location:** `data/synthetic/`
- **Script:** `scripts/generate_runtime_data.py`
- **Seed:** `43`
- **Accounts:** 50 (IDs: `ACME-EU-90001` to `ACME-EU-90050`)
- **Status:** committed to repo
- **Special:** no labels, includes engineered conflict accounts + golden path

## File Cardinality

| File | Cardinality | Training Rows | Runtime Rows |
|---|---|---|---|
| accounts.csv | 1:1 master | 2,500 | 50 |
| opportunities.csv | 1:N (exactly 4 per account) | 10,000 | 200 |
| snowflake_metrics.csv | 1:1 (pre-aggregated) | 2,500 | 50 |
| external_funds.csv | 1:N (~60% coverage) | ~1,500 | ~30 |
| conferences.csv | catalog (~25 conferences) | ~25 | ~25 |
| conference_attendance.csv | M:N join (~2.5 per account) | ~6,250 | ~125 |

## Engineered Demo Accounts (Runtime — 17 of 50)

| Group | Count | Purpose |
|---|---|---|
| Golden path (`ACME-EU-90001`) | 1 | 4 won opps, 5 tier-1 conferences, 2 fund launches → Bucket A |
| Engineered conflicts | 3 | High ML + zero context (or vice versa) → `conflict_flag=True` |
| Clear Bucket C | 5 | All lost opps, no conferences, no funds → trivial Bucket C |
| Borderline | 8 | Mixed signals near decision boundaries |
| Background | 33 | Naturally distributed across A/B/C |

## Hidden Label Function

Used by `generate_training_data.py` to assign opportunity `status`:

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

**Critical:** `win_rate` is NOT in the label function — it would be circular since `win_rate` is derived from these labels.

## Conference Attendance Distribution

- ~30% of accounts attend 0 conferences
- ~40% attend 1-2
- ~25% attend 3-6
- ~5% are regulars with 7+
- Average: ~2.5 per account

## How to Regenerate

### Training data
```bash
python scripts/generate_training_data.py
```
Generates 2,500 accounts + all 1:N tables into `data/training/`. Gitignored.

### Runtime data
```bash
python scripts/generate_runtime_data.py
```
Generates 50 accounts + all 1:N tables into `data/synthetic/`. Committed.

## Validation Checks

After generating, verify:
1. Row counts match expected cardinality (see table above)
2. No orphaned foreign keys (every `account_id` in child tables exists in accounts.csv)
3. No duplicates in primary keys
4. ID ranges don't overlap between training and runtime
5. ~35% positive class rate on training opportunity labels
6. Conference catalog is identical between training and runtime sets
7. Golden path account `ACME-EU-90001` has the expected profile (4 won, 5 tier-1 confs, 2 fund launches)

## Important Rules

- **NEVER use real client data** — all data is 100% synthetic
- **NEVER edit data/training/ by hand** — always regenerate via script
- **Both generators MUST use shared functions from `app/data_gen.py`** to prevent distribution skew
- **Seeds are locked:** 42 for training, 43 for runtime
