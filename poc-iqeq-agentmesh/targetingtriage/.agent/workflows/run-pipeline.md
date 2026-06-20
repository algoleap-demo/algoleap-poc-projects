---
description: How to run the full POC1 Targeting & Triage pipeline from scratch
---

# Run Pipeline Workflow

Step-by-step instructions to run the full POC1 pipeline from data generation to API response.

## Prerequisites

- Python 3.11+
- All dependencies installed: `pip install -r requirements.txt`
- LLM provider configured via environment variable (for Reasoning Agent)

## Steps

### 1. Generate training data (one-time, if not already done)

```bash
python scripts/generate_training_data.py
```

- Generates 2,500 accounts + all 1:N tables into `data/training/`
- Seed: 42
- Verify: ~22,775 total rows across 6 CSV files

### 2. Train the XGBoost model (one-time, if not already done)

```bash
python scripts/train_xgb.py
```

- Produces `models/xgb_propensity_v1.pkl`
- Produces `models/score_distribution.png`
- Verify: test AUC >= 0.75 printed to console
- Verify: histogram shows reasonable score spread

### 3. Generate runtime data (one-time, if not already done)

```bash
python scripts/generate_runtime_data.py
```

- Generates 50 accounts + all 1:N tables into `data/synthetic/`
- Seed: 43
- Verify: ~480 total rows across 6 CSV files
- Verify: golden path account `ACME-EU-90001` has expected profile

### 4. (Optional) Retune ML threshold

After steps 2 and 3, inspect the score distribution on the runtime 50 accounts.
If most scores cluster between 0.4-0.6, lower `ML_HIGH_THRESHOLD` in `app/constants.py`.

### 5. Run tests

```bash
pytest tests/
```

- `test_feature_parity.py` — asserts features.py is deterministic
- `test_golden_path.py` — ACME-EU-90001 end-to-end check

### 6. Start the FastAPI server

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Trigger the pipeline

```bash
curl -X POST http://localhost:8000/score_accounts
```

Or use the Swagger UI at `http://localhost:8000/docs`.

### 8. Validate the response

Check the JSON response for:
- [ ] All 50 accounts present
- [ ] Each account has: account_id, priority_bucket, ml_score, confidence_level, conflict_flag, rationale_text, nba_actions
- [ ] At least 2 of 3 engineered conflict accounts have `conflict_flag=True`
- [ ] Golden path `ACME-EU-90001` returns Bucket A
- [ ] NBA actions match deterministic rules (A=call/5, B=send_link/10, C=schedule/90)

### 9. Check audit logs

```bash
cat logs/audit.jsonl
```

- Should contain one entry per agent per run (6 entries total)

### 10. Check governance queue

```bash
cat logs/governance_queue.jsonl
```

- Should contain flagged accounts with `conflict_flag=True`

## Quick Start (if all data/model already exists)

```bash
# Start server
uvicorn app.main:app --reload --port 8000

# Hit the endpoint
curl -X POST http://localhost:8000/score_accounts
```

## Troubleshooting

| Issue | Solution |
|---|---|
| Feature mismatch error on scoring | Feature order in code doesn't match pickle. Retrain with `python scripts/train_xgb.py` |
| All scores clustered near 0.5 | Calibration may need tuning. Check `models/score_distribution.png` |
| No conflicts detected | Check that engineered conflict accounts exist in `data/synthetic/accounts.csv` |
| LLM timeout | Check LLM provider env var and connectivity |
| Missing CSV files | Run `python scripts/generate_runtime_data.py` |
