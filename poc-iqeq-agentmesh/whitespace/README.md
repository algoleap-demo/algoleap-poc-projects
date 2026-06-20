# POC3 — Whitespace Analysis

## Overview
POC3 identifies whitespace opportunities from the shared account–product matrix, clusters accounts, and produces **three cluster-level campaign briefs** via **OpenRouter**. Implementation lives in the unified repo:

- **Module**: [`app/modules/whitespace/`](../app/modules/whitespace/)
- **Requirements**: [`requirements/POC3_Requirements_v3.md`](requirements/POC3_Requirements_v3.md)
- **Context & standards**: [`context.md`](context.md)
- **Milestones**: [`plan.md`](plan.md)

## Configuration
Create or extend the repo-root `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
POC3_LLM_MODEL=anthropic/claude-3.5-sonnet
```

Swap models by changing `POC3_LLM_MODEL` only (e.g. `openai/gpt-4o-mini`).

## How to Run

### HTTP (unified app)
From repo root:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then:

```http
POST /analyze_whitespace
Content-Type: application/json

{}
```

Optional filters:

```json
{
  "countries": ["NL", "DE"],
  "segment": "PIAO",
  "product_ids": ["P-ESG", "P-DEP"]
}
```

### CLI (console logs)
Sequential agent progress is printed to stdout:

```bash
python scripts/run_poc3.py
```

## Outputs
- **JSON**: `whitespace_grid`, `top_accounts`, `campaign_briefs`, `validation_flags`, `export_csv_path`.
- **CSV**: `outputs/whitespace_top50_<pipeline_run_id>.csv` (50 rows; padded only if fewer than 50 qualifying cells exist).
- **Logs**: `logs/audit.jsonl`, `logs/governance_queue.jsonl`.

## Data
POC3 reads **`data/raw/`** only (no separate generator). The demo uses **six** products; clustering and heatmap dimensions follow `product_catalog.csv`.
