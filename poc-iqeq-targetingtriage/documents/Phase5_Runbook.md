# Phase 5 Runbook - ISO 42001 Governance Workbench

Phase 5 adds a browser-based governance workbench and audit trail for human-in-the-loop oversight of LLM-generated account prioritisations.

## Components

| Component | Description |
|-----------|-------------|
| Backend API | `POST /overrides`, `GET /overrides`, `GET /overrides/summary` |
| Frontend UI | React SPA served at `/ui/` — Prioritisation view + Audit dashboard |
| SQLite table | `audit_overrides` in `data/triage_poc.db` |

## Prereqs

- Phase 3 and 4 completed (SQLite has `accounts`, `scored_accounts`)
- Environment variable: `GEMINI_API_KEY` (for live LLM calls)

## Run the application

```bash
cd data/scripts
python -m uvicorn scoring_api:app --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000** (auto-redirects to `/ui/`)

## Usage

### 1. Prioritise Accounts

- Navigate to **Prioritisation** in the sidebar
- Set filters (countries, status, min propensity, limit)
- Click **Prioritise** — calls Gemini and displays A/B/C ranked results
- Click **Export CSV** to download the ranked list

### 2. Override an AI Decision

- Click **Override** on any account row
- Modify the priority bucket and/or rationale
- **Required:** Select a failure category (Policy Misalignment / Hallucination / Data Latency)
- Add optional notes and save

### 3. Review Audit Trail

- Navigate to **Audit Dashboard**
- View aggregate stats (total overrides, breakdown by category)
- Donut and bar charts show failure category distribution
- Filter and review the full override log table

## API Endpoints

### POST /overrides

```bash
curl -X POST http://localhost:8000/overrides ^
  -H "Content-Type: application/json" ^
  -d "{\"account_id\":\"ACC_LU_0001\",\"field_changed\":\"priority_bucket\",\"old_value\":\"B\",\"new_value\":\"A\",\"failure_category\":\"Hallucination\"}"
```

### GET /overrides

```bash
curl http://localhost:8000/overrides
curl "http://localhost:8000/overrides?failure_category=Hallucination"
```

### GET /overrides/summary

```bash
curl http://localhost:8000/overrides/summary
```

## Tests (offline, Gemini mocked)

```bash
python -m pytest tests/test_phase5_overrides.py -v
```
