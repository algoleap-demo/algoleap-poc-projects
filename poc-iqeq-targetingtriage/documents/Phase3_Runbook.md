# Phase 3 Runbook - SQLite-backed Scoring API

This runbook executes Phase 3 end-to-end using **synthetic data**, **SQLite** as the backend store, and a **FastAPI** scoring service.

## Prereqs

- Python installed and available as `python`
- Dependencies (one-time):

```bash
pip install pandas numpy faker scikit-learn xgboost fastapi uvicorn pytest httpx
```

## Step 1 - Generate synthetic data (CSVs)

```bash
python data/scripts/generate_synthetic_data.py
```

Outputs go to `data/synthetic_data/`:
- `accounts.csv`
- `opportunities.csv`
- `snowflake_metrics.csv`
- `external_funds.csv`
- `conferences.csv`

## Step 2 - Load into SQLite (mandatory)

```bash
python data/scripts/load_to_sqlite.py
```

Creates/overwrites SQLite DB at `data/triage_poc.db` with tables:
- `accounts`
- `opportunities`
- `snowflake_metrics`
- `external_funds`
- `conferences`

## Step 3 - Train + score + persist scored table

```bash
python data/scripts/train_propensity_model.py
```

Outputs:
- SQLite table `scored_accounts` written into `data/triage_poc.db`
- Artifacts written to `data/model_artifacts/`:
  - `scored_accounts.csv`
  - `feature_cols.json`
  - `eval_report.json`
  - `{best_model}_propensity.pkl`

## Step 4 - Run the API (SQLite-backed)

```bash
cd data/scripts
python -m uvicorn scoring_api:app --host 0.0.0.0 --port 8000
```

### Environment variables (optional)

- `TRIAGE_DB_PATH`: override default SQLite path.
  - Default: `data/triage_poc.db` (resolved relative to `data/scripts/scoring_api.py`)

Example:

```bash
set TRIAGE_DB_PATH=C:\full\path\to\triage_poc.db
```

## Step 5 - Smoke tests

Health:

```bash
curl http://localhost:8000/health
```

Score accounts (example):

```bash
curl -X POST http://localhost:8000/score_accounts ^
  -H "Content-Type: application/json" ^
  -d "{\"countries\": [\"LU\", \"NL\"], \"limit\": 30}"
```

Account view:

```bash
curl http://localhost:8000/account_view/ACC_LU_0001
```

## Step 6 - Automated integration tests

```bash
python -m pytest
```

If tests fail with `503 Model artifacts not loaded`, verify Step 2 (SQLite load) and Step 3 (training wrote `scored_accounts`).

