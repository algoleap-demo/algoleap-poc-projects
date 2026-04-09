---
description: Algoleap POC project rules - auto-applied to all agent sessions
---

# POC Context
- Client: IQ-EQ
- POC type: GenAI-Agent (ML + LLM agentic pipeline)
- Stack: Python 3.11+ / FastAPI / XGBoost / Multi-provider LLM router
- Deploy target: Local development (rapid prototype)

# Architecture rules
- 6 agents total: Orchestration + 5 specialist (Data, Scoring, Reasoning, Validation, Formatting)
- Pipeline is LINEAR: Orchestration -> Data -> Scoring -> Reasoning -> Validation -> Formatting -> Orchestration -> User
- Single API endpoint: POST /score_accounts
- No database - in-memory + JSONL log files
- No auth, no persistence, no retries

# Scope boundaries
- Only create or modify files inside app/, scripts/, tests/, data/, models/, logs/
- Do not touch .env or .gitignore
- Do not modify the trained model pickle at models/xgb_propensity_v1.pkl
- Do not modify files in data/training/ by hand (regenerate via scripts/generate_training_data.py)
- All new Python files must have a requirements entry if they add a new package
- All changes must respect the locked project layout in the scope contract

# Feature engineering rules
- app/features.py is the SINGLE SOURCE OF TRUTH for feature aggregation
- features.py MUST be used identically by training scripts AND runtime scoring
- Never duplicate feature logic - always import from features.py
- The 8 features are locked: win_rate, avg_deal_size_eur, open_opps_count, service_penetration, engagement_score, launch_indicator, tier_1_conf_count, growth_metrics_qoq

# Agent boundary rules
- Reasoning Agent must NEVER recalculate or override ML scores
- NBA actions are deterministic rule-based lookups in Formatting Agent - NEVER LLM inferences
- Validation Agent must ALWAYS surface conflicts - never silently suppress them
- All agent outputs must conform to Pydantic schemas in app/schemas.py
- Formatting Agent enforces schema validation on the final payload

# ML rules
- XGBoost with isotonic calibration (CalibratedClassifierCV)
- ML_HIGH_THRESHOLD = 0.70, ML_LOW_THRESHOLD = 0.30 (provisional, may retune post-training)
- Scoring Agent must assert feature column order matches pickle's feature_names
- Fixed seeds: 42 for training, 43 for runtime

# Data rules
- All data is 100% synthetic - never ask for or use real client data
- Training data (2,500 accounts): data/training/ - gitignored, regenerable via script
- Runtime data (50 accounts): data/synthetic/ - committed to repo
- ID ranges: Training ACME-EU-00001 to ACME-EU-02500, Runtime ACME-EU-90001 to ACME-EU-90050
- 6 CSV files: accounts, opportunities, snowflake_metrics, external_funds, conferences, conference_attendance
- Both generators use shared functions from app/data_gen.py

# Naming conventions
- Python functions: snake_case
- Agent files: snake_case (e.g., data_agent.py, scoring_agent.py)
- Pydantic models: PascalCase
- API routes: POST /score_accounts (single endpoint in v1)

# Logging and audit
- Audit log: logs/audit.jsonl - one line per agent invocation per run
- Governance queue: logs/governance_queue.jsonl - conflict_flag=True accounts appended here
- Error handling: fail loudly with structured exception, no retries

# Commit message format
- feat: short description (new feature)
- fix: short description (bug fix)
- data: short description (data changes)
- docs: short description (docs only)
