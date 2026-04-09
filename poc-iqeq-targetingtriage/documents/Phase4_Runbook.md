# Phase 4 Runbook - LLM Orchestration (Gemini)

Phase 4 adds an orchestration endpoint that calls Phase 3 scoring and then uses **Gemini** to produce a structured output:

- `account_id`
- `priority_bucket` (A/B/C)
- `rationale_text` (1-3 sentences)

## Prereqs

- Phase 3 completed (SQLite has `accounts` and `scored_accounts`)
- Environment variable set:
  - `GEMINI_API_KEY`

Optional:
- `GEMINI_MODEL` (default: `gemini-flash-latest`)
- `TRIAGE_DB_PATH` (default: `data/triage_poc.db`)

## One-time install

```bash
pip install fastapi uvicorn pandas
```

## Run the API

```bash
cd data/scripts
python -m uvicorn scoring_api:app --host 0.0.0.0 --port 8000
```

## Call Phase 4 endpoint

### Example 1 - NL + LU top 30

```bash
curl -X POST http://localhost:8000/prioritize_accounts ^
  -H "Content-Type: application/json" ^
  -d "{\"countries\":[\"NL\",\"LU\"],\"limit\":30}"
```

### Example 2 - Prospects only + minimum propensity

```bash
curl -X POST http://localhost:8000/prioritize_accounts ^
  -H "Content-Type: application/json" ^
  -d "{\"status_filter\":\"prospect\",\"min_propensity\":0.4,\"limit\":25}"
```

## Output contract

Response envelope:
- `prompt_version`
- `llm_provider` (= gemini)
- `llm_model`
- `generated_at_utc`
- `results`: array of `{account_id, priority_bucket, rationale_text}`

The service enforces:
- Output must be valid JSON (no markdown fences)
- No unknown `account_id` values
- `priority_bucket` must be A/B/C

## Prompt assets

Prompts are stored and version-controlled under:
- `documents/prompts/phase4_system.md`
- `documents/prompts/phase4_user_template.md`

## Tests (offline, Gemini mocked)

```bash
python -m pytest
```

