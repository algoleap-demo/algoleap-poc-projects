# IQ-EQ Unified Agent Mesh — Handover & Runbook

**For:** Engineers or consultants taking over deployment, demos, or hardening.  
**Architecture detail:** See [`ARCHITECTURE.md`](ARCHITECTURE.md). **Integration map:** [`context.md`](context.md). **Milestone checklist:** [`plan.md`](plan.md).

---

## 1. Repository layout (what matters)

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, routes, LangGraph full mission, static mount |
| `app/core/` | `llm_client`, `progress_tracker`, `audit_logger`, `constants`, `features*` |
| `app/modules/targeting/` | POC1 pipeline |
| `app/modules/planning/` | POC2 pipeline |
| `app/modules/whitespace/` | POC3 pipeline |
| `app/static/` | `index.html`, `mesh_architecture.svg`, `shared_styles.css` |
| `data/raw/` | CSV backbone (`accounts`, `contacts`, `account_product_matrix`, `product_catalog`, …) |
| `models/` | `xgb_propensity_v1.pkl` |
| `outputs/` | POC3 CSV exports (gitignored) |
| `logs/` | `audit.jsonl`, `governance_queue.jsonl` (as configured) |
| `tests/` | Pytest (incl. POC3 golden path with mocked LLM) |

Legacy folders `targetingtriage/`, `accountplanning/` may contain older copies — **authoritative code is `app/`**.

---

## 2. Environment variables (`.env`)

Create `.env` at the **repo root** (same level as `app/`).

| Variable | Required for | Notes |
|----------|----------------|-------|
| `OPENROUTER_API_KEY` | **POC2** brief + call plan, **POC3** campaign briefs | Primary demo path |
| `OPENROUTER_MODEL` | Default model id on OpenRouter | e.g. `anthropic/claude-3.5-sonnet` |
| `OPENROUTER_BASE_URL` | Optional | Default `https://openrouter.ai/api/v1` |
| `POC2_LLM_MODEL` | Optional | Override model for planning only |
| `POC3_LLM_MODEL` | Optional | Override model for POC3 campaigns |
| `GOOGLE_API_KEY` | POC1 reasoning if no OpenAI/Groq/OpenRouter | Gemini |
| `OPENAI_API_KEY` | POC1 reasoning fallback | |
| `GROQ_API_KEY` | POC1 reasoning fallback | |

**POC2 planning does not use `get_model()`** — it uses **`get_planning_model()`** → OpenRouter **only**.

---

## 3. Run locally

```bash
cd <repo-root>
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

Open **http://127.0.0.1:8010/** (use another port if 8010/8000 is taken on Windows).

**Dashboard behavior (current):**

- **Tabs** drive which mission log/output is shown; clicking an enabled tab **starts** the next pending phase (Targeting → Account Planning → Whitespace).
- Live logs: **Server-Sent Events** `GET /events`.
- After a run completes, **mission output** unlocks (results + hint text).

---

## 4. API quick test

```bash
# POC1 (await full run)
curl -X POST http://127.0.0.1:8010/run/poc1

# Results snapshot
curl http://127.0.0.1:8010/mission_results
```

POC2 requires POC1 results in `mission_store` (use dashboard flow or call `/run/poc1` first in the same server process).

---

## 5. Common failures

| Symptom | Likely cause | Mitigation |
|---------|--------------|------------|
| Strategic brief / call plan errors | OpenRouter rate limit, model rejects JSON mode, missing key | Check `.env`; set `POC2_LLM_MODEL`; code falls back to **offline** brief/call plan with a model note |
| POC3 HTTP 502 | Exception in pipeline (see server log) | Fixed historical `cluster_members` KeyError; check `sklearn`, data shapes |
| Dashboard output stuck on “Results unlock…” | Old client not resolving POST completion | Current `index.html` finishes on **successful POST** + SSE patterns; hard refresh |
| XGBoost / empty propensity | Missing `models/xgb_propensity_v1.pkl` | Code uses neutral **0.5** propensity with warning telemetry |

---

## 6. Tests

```bash
pytest tests/ -q
```

POC3 golden path **mocks** `run_poc3_campaign_chain` so CI does not require live LLM.

---

## 7. Extending for production (explicit non-goals today)

- No production **auth/RBAC** on routes.
- No **Snowflake/CRM** connectors in this repo (CSV only).
- **Governance workbench** tray is not fully wired to live queue UI (JSONL append exists for flags).

---

## 8. Stakeholder demo script (5 minutes)

1. Show **mesh** (left) vs **logs + output** (right) — explain **human-in-the-loop** tabs.
2. Run **Targeting** — mention **XGBoost** + **LLM rationale** + validation.
3. Run **Account Planning** — mention **API score** formula and **OpenRouter** brief + call plan.
4. Run **Whitespace** — mention **heatmap**, **k-means**, **three** campaign briefs, **CSV** path.
5. Point to **`ARCHITECTURE.md`** for formulas and compliance talk-track.

---

*Handover version: 2026-04.*
