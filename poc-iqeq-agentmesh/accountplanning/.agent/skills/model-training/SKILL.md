---
name: model-training
description: How to train, calibrate, and validate the XGBoost propensity model for POC1 Targeting & Triage
---

# Model Training Skill

This skill documents the end-to-end process for training the XGBoost propensity model used by the Scoring Agent.

## Overview

The model is a **one-shot offline training** — run once, commit the resulting pickle. The Scoring Agent loads the pickle at runtime and predicts propensity scores for the 50 runtime accounts.

## Prerequisites

- Training data generated in `data/training/` (see `data-generation` skill)
- `app/features.py` must be finalized (shared between training and runtime)
- Required packages: `xgboost`, `scikit-learn`, `joblib`, `pandas`, `numpy`, `matplotlib`

## Training Pipeline

### Step 1: Feature Aggregation

The training script calls `app/features.py` → `compute_features()` for each of the 2,500 training accounts, producing a **2,500 x 8 feature matrix**.

The 8 features (locked):

| Feature | Description | Source |
|---|---|---|
| win_rate | Wins / closed opportunities | opportunities |
| avg_deal_size_eur | Mean deal size | opportunities |
| open_opps_count | Currently open opportunities | opportunities |
| service_penetration | Service adoption depth (0-1) | snowflake_metrics |
| engagement_score | Composite of usage + conference attendance | snowflake_metrics + conference_attendance |
| launch_indicator | Recent fund launch in last 90 days (0/1) | external_funds |
| tier_1_conf_count | Number of tier-1 conferences attended | conference_attendance + conferences |
| growth_metrics_qoq | Period-over-period revenue growth | snowflake_metrics |

### Step 2: Label Derivation

Account-level label: `account_won_majority = (win_rate >= 0.5)`

This is derived from the opportunity-level `won_deal` labels after feature aggregation.

### Step 3: Train/Test Split

```
70% train / 15% validation / 15% test
Stratified on account_won_majority
Fixed seed: 42
Yields: ~1,750 train / ~375 val / ~375 test accounts
```

### Step 4: XGBoost Training

```python
XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric="logloss",
)
```

### Step 5: Isotonic Calibration

```python
CalibratedClassifierCV(method="isotonic", cv=3)
```

**Why:** XGBoost outputs are over-confident at extremes. The conflict detection thresholds (`ML_HIGH_THRESHOLD = 0.70`) depend on calibrated probabilities to fire correctly.

### Step 6: Evaluation

Print and verify:
- **AUC on test set >= 0.75** (synthetic data ceiling ~0.85)
- Confusion matrix at 0.5 threshold
- Score distribution histogram saved to `models/score_distribution.png`

### Step 7: Save Pickle

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

## How to Train

```bash
python scripts/train_xgb.py
```

## Acceptance Criteria

- [ ] Test AUC >= 0.75
- [ ] `models/score_distribution.png` shows reasonable spread (not clustered at 0 or 1)
- [ ] `ML_HIGH_THRESHOLD` retuned if histogram on runtime 50 shows clustering
- [ ] Feature order in pickle matches `FEATURE_ORDER` in `app/constants.py`

## Post-Training Verification

After training, **inspect the score distribution on the runtime 50 accounts**:
- If most scores cluster between 0.4-0.6, lower `ML_HIGH_THRESHOLD`
- The value 0.70 is provisional until calibration is verified
- Update `app/constants.py` if threshold changes

## Runtime Contract

The Scoring Agent:
1. Loads the pickle from `models/xgb_propensity_v1.pkl`
2. Asserts `df.columns.tolist() == feature_names` from the pickle
3. Fails loudly on mismatch

**This assertion is the single most likely place to catch a silent bug.** Never skip it.

## Important Rules

- **NEVER modify the pickle by hand** — always retrain via script
- **features.py is the single source of truth** — training and runtime MUST use the same function
- **Seeds are locked** — seed 42 for all training randomness
- **Calibration is mandatory** — raw XGBoost probabilities are unreliable for threshold rules
