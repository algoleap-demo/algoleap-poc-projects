# Algoleap POC Project Setup Guide

> \*\*Add this file as `POC\_SETUP.md` at the root of every new POC repo before writing any code.\*\*  
> Follow the steps in order. The whole setup should take under 30 minutes.

\---

## Step 1 — Create the GitHub Repo

\---

## Step 2 — Environment Files

Create a `.env` file at the project root. **Never commit this file to GitHub.**

```bash
touch .env
echo ".env" >> .gitignore
```

Paste the template below and fill in your keys:
|---|---|---||---|---|---||---|---|---||---|---|---|

```env
# ── GenAI APIs ──────────────────────────────────────────────
# Gemini (use for development and iteration loops)
GEMINI\_API\_KEY=your\_gemini\_api\_key\_here
# Register at: https://aistudio.google.com/app/apikey
# Important: use a SEPARATE key from the one configured in Cursor IDE
# Each key gets its own 1M tokens/day free quota

# Claude (use for final demo delivery only)
ANTHROPIC\_API\_KEY=your\_anthropic\_api\_key\_here
# Register at: https://console.anthropic.com
# Models: claude-haiku-4-5 (fast/cheap), claude-sonnet-4-6 (best quality)

# Groq (fallback when Gemini quota is exhausted mid-sprint)
GROQ\_API\_KEY=your\_groq\_api\_key\_here
# Register at: https://console.groq.com

# ── Database (RAG projects only) ─────────────────────────────
SUPABASE\_URL=your\_supabase\_project\_url
SUPABASE\_KEY=your\_supabase\_anon\_key
# Register at: https://supabase.com — free 500MB tier

# ── App Config ───────────────────────────────────────────────
APP\_ENV=development
PORT=8000
```

## Step 3 — Create a Readme markdown file for your project

1. What type of POC
2. What are the key functionalities in the POC
3. What are the key features
4. Based on the POC tech spec create a step by step process to be developed for the project.

## |---|---|---||---|---|---||---|---|---||---|---|---|

## Step 4 — Identify Your POC Type

Choose one path below. If your POC spans multiple types (e.g. an ML model served via a React dashboard), follow the **Full-Stack** path — it includes everything.

|POC Type|What it involves|Go to|
|-|-|-|
|**ML / Data**|Prediction, scoring, anomaly detection, dashboards|[Path A](path-a--ml--data-poc.md)|
|**Full-Stack**|React frontend + FastAPI backend + ML or GenAI|[Path B](path-b--full-stack-poc.md)|
|**GenAI / Agent**|LangGraph agents, tool use, multi-agent orchestration|[Path C](path-c--genai--agent-poc.md)|
|**RAG**|Document Q\&A, knowledge base, semantic search|[Path D](path-d--rag-poc.md)|



## Step 5 —

### Project-level rules (add to each POC repo)

Create this folder and file at the root of every new POC project:

```bash
mkdir -p .cursor/rules
```

Then create `.cursor/rules/poc-rules.mdc` with the following content — edit the top section for each POC:

```markdown
---
description: Algoleap POC project rules — auto-applied to all agent sessions
---

# POC Context
- Client: \[CLIENT NAME]
- POC type: \[ML / Full-Stack / GenAI-Agent / RAG]
- Stack: FastAPI + \[React+Vite / Streamlit] + \[SQLite / Supabase]
- Deploy target: \[Vercel + Railway / Streamlit Community Cloud]

# Scope boundaries
- Only create or modify files inside /backend and /frontend directories
- Do not touch .env, .gitignore, or POC\_SETUP.md
- Do not modify trained model files in /models/trained/
- All new Python files must have a requirements entry if they add a new package

# Naming conventions
- Python functions: snake\_case
- React components: PascalCase, file name matches component name
- API routes: /api/\[resource] — plural nouns, no verbs
- SQLite tables: snake\_case, plural

# Demo data rules
- All data is synthetic — never ask for or use real client data
- Synthetic datasets go in /data/raw/ before processing
- Processed datasets go in /data/processed/

# Commit message format
- feat: short description (new feature)
- fix: short description (bug fix)
- data: short description (data changes)
- docs: short description (docs only)
```

## Step 6 — Final Checks Before First Commit

Run through this checklist before pushing to GitHub:

```
\[ ] .env is listed in .gitignore — verify with: git status (should NOT show .env)
\[ ] All API keys are in .env only — not hardcoded in any .py or .js file
\[ ] Repo is set to Private on GitHub
\[ ] Repo name follows convention: poc-\[client]-\[topic]
\[ ] requirements.txt exists and is up to date: pip freeze > requirements.txt
\[ ] App runs locally without errors before first push
\[ ] README.md has: client name, POC type, how to run locally, demo URL (add after deploy)
```

### First commit

```bash
git add .
git commit -m "feat: initial POC scaffold — \[client] \[topic]"
git push origin main
```

