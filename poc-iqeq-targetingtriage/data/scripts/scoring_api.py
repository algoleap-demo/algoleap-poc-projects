"""
IQ-EQ Targeting & Triage Agent — Scoring API
=============================================
Exposes endpoints for the Configured LLM orchestration layer:

  POST /score_accounts         — returns scored + prioritised list
  GET  /account_view/{id}      — returns single account detail view
  POST /prioritize_accounts    — LLM orchestration (Phase 4)
  POST /overrides              — record a human override (Phase 5)
  GET  /overrides              — list audit override records
  GET  /overrides/summary      — aggregated override stats

Usage:
    pip install fastapi uvicorn pandas
    python scoring_api.py

Then call:
    curl -X POST http://localhost:8000/score_accounts \
      -H "Content-Type: application/json" \
      -d '{"countries": ["LU", "NL"], "limit": 30}'
"""

import json
import os
import re
from datetime import datetime, timezone
import sqlite3
from typing import Literal, Optional

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    # Works when running from repo root (preferred)
    from data.scripts.gemini_client import GeminiError, generate_text  # type: ignore
except ModuleNotFoundError:
    # Works when running from data/scripts
    from gemini_client import GeminiError, generate_text  # type: ignore

app = FastAPI(
    title="IQ-EQ Targeting & Triage Scoring API",
    description="Propensity scores and account prioritisation for FAM/PIAO Continental Europe",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load from SQLite at startup ──────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB_PATH = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "triage_poc.db"))
DB_PATH = os.getenv("TRIAGE_DB_PATH", _DEFAULT_DB_PATH)


def load_scored_accounts_from_sqlite() -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"SQLite DB not found at {DB_PATH}. Run load_to_sqlite.py first."
        )
    with sqlite3.connect(DB_PATH) as connection:
        scored_cols = [
            row[1]
            for row in connection.execute("PRAGMA table_info(scored_accounts)").fetchall()
        ]
        # Avoid duplicate column names from join (accounts is source of truth for these).
        scored_cols = [
            c for c in scored_cols
            if c not in {"name", "country", "segment", "status", "key_contact", "last_contact_date", "strategic_priority_flag"}
        ]
        scored_select = ", ".join([f"s.\"{c}\"" for c in scored_cols])
        query = f"""
            SELECT
                {scored_select},
                a.name,
                a.country,
                a.segment,
                a.status,
                a.key_contact,
                a.last_contact_date,
                a.strategic_priority_flag
            FROM scored_accounts s
            LEFT JOIN accounts a
                ON a.account_id = s.account_id
        """
        return pd.read_sql_query(query, connection)


try:
    merged_df = load_scored_accounts_from_sqlite()
    print(f"Loaded {len(merged_df)} scored accounts from SQLite.")
except (FileNotFoundError, pd.io.sql.DatabaseError, sqlite3.Error) as e:
    print(f"WARNING: Could not load SQLite data - {e}")
    print("Ensure you ran: load_to_sqlite.py then train_propensity_model.py")
    merged_df = pd.DataFrame()


# ── Initialise audit_overrides table ─────────────────────────────────────────

def _init_audit_table():
    if not os.path.exists(DB_PATH):
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT NOT NULL,
                account_id TEXT NOT NULL,
                field_changed TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                failure_category TEXT NOT NULL,
                notes TEXT
            )
        """)
        conn.commit()

_init_audit_table()


# ── Request / Response schemas ───────────────────────────────────────────────

class ScoreRequest(BaseModel):
    countries: Optional[list[str]] = None       # e.g. ["LU", "NL"]
    segments: Optional[list[str]] = None        # ["FAM", "PIAO"]
    status_filter: Optional[str] = None         # "client" | "prospect" | None (all)
    min_propensity: Optional[float] = 0.0
    limit: Optional[int] = 50


class AccountBrief(BaseModel):
    account_id: str
    name: str
    country: str
    segment: str
    status: str
    priority_bucket: str
    ICP_fit_score: float
    buy_upsell_propensity: float
    whitespace_flag: bool
    upcoming_launch_flag: bool
    last_contact_date: Optional[str]


class AccountDetail(BaseModel):
    account_id: str
    name: str
    country: str
    segment: str
    status: str
    key_contact: str
    last_contact_date: Optional[str]
    priority_bucket: str
    ICP_fit_score: float
    buy_upsell_propensity: float
    whitespace_flag: bool
    upcoming_launch_flag: int
    features: dict


class PrioritizeRequest(BaseModel):
    countries: Optional[list[str]] = None
    segments: Optional[list[str]] = None
    status_filter: Optional[str] = None
    min_propensity: Optional[float] = 0.0
    limit: Optional[int] = 30
    prompt_version: Optional[str] = "v1"


class PrioritizedAccount(BaseModel):
    account_id: str
    priority_bucket: str
    rationale_text: str


class PrioritizeResponse(BaseModel):
    prompt_version: str
    llm_provider: str
    llm_model: str
    generated_at_utc: str
    results: list[PrioritizedAccount]


_VALID_FAILURE_CATEGORIES = {"Policy Misalignment", "Hallucination", "Data Latency"}
_VALID_FIELDS_CHANGED = {"priority_bucket", "rationale_text"}


class OverrideRequest(BaseModel):
    account_id: str
    field_changed: str
    old_value: str
    new_value: str
    failure_category: str
    user: str = Field(default="analyst@iqeq.com")
    notes: Optional[str] = None


class OverrideRecord(BaseModel):
    id: int
    timestamp: str
    user: str
    account_id: str
    field_changed: str
    old_value: Optional[str]
    new_value: Optional[str]
    failure_category: str
    notes: Optional[str]


class OverrideSummary(BaseModel):
    by_category: dict[str, int]
    by_field: dict[str, int]
    total: int


class CopilotRequest(BaseModel):
    message: str


class CopilotResponse(BaseModel):
    reply: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "loaded_accounts": len(merged_df)}


@app.post("/score_accounts", response_model=list[AccountBrief])
def score_accounts(req: ScoreRequest):
    """
    Returns a ranked list of accounts filtered by country, segment, status,
    and minimum propensity score. Sorted descending by buy_upsell_propensity.
    """
    if merged_df.empty:
        raise HTTPException(status_code=503, detail="Model artifacts not loaded.")

    df = merged_df.copy()

    if req.status_filter and req.status_filter not in {"client", "prospect"}:
        raise HTTPException(status_code=422, detail="status_filter must be client|prospect")

    if req.countries:
        df = df[df["country"].isin(req.countries)]
    if req.segments:
        df = df[df["segment"].isin(req.segments)]
    if req.status_filter:
        df = df[df["status"] == req.status_filter]
    if req.min_propensity and req.min_propensity > 0:
        df = df[df["buy_upsell_propensity"] >= req.min_propensity]

    limit = req.limit or 50
    limit = max(1, min(int(limit), 500))

    df = df.sort_values(
        ["buy_upsell_propensity", "ICP_fit_score"],
        ascending=[False, False],
    ).head(limit)

    return [
        AccountBrief(
            account_id=row["account_id"],
            name=row["name"],
            country=row["country"],
            segment=row["segment"],
            status=row["status"],
            priority_bucket=row["priority_bucket"],
            ICP_fit_score=round(float(row["ICP_fit_score"]), 4),
            buy_upsell_propensity=round(float(row["buy_upsell_propensity"]), 4),
            whitespace_flag=bool(row["whitespace_flag"]),
            upcoming_launch_flag=bool(row["upcoming_launch_flag"]),
            last_contact_date=row.get("last_contact_date"),
        )
        for _, row in df.iterrows()
    ]


@app.get("/account_view/{account_id}", response_model=AccountDetail)
def account_view(account_id: str):
    """
    Returns full account detail including all ML features.
    Used by the LLM orchestration layer to generate rationale.
    """
    if merged_df.empty:
        raise HTTPException(status_code=503, detail="Model artifacts not loaded.")

    row_df = merged_df[merged_df["account_id"] == account_id]
    if row_df.empty:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found.")

    row = row_df.iloc[0]
    features = {
        "historic_win_rate": round(float(row.get("historic_win_rate", 0)), 4),
        "avg_deal_size_eur": int(row.get("avg_deal_size_eur", 0)),
        "opp_count": int(row.get("opp_count", 0)),
        "revenue_concentration": round(float(row.get("revenue_concentration", 0)), 4),
        "yoy_revenue_growth": round(float(row.get("yoy_revenue_growth", 0)), 4),
        "service_penetration_score": round(float(row.get("service_penetration_score", 0)), 4),
        "existing_middle_office_flag": bool(row.get("existing_middle_office_flag", False)),
        "esg_policy_support_flag": bool(row.get("esg_policy_support_flag", False)),
        "total_fund_aum": int(row.get("total_fund_aum", 0)),
        "current_aum_with_iqeq": int(row.get("current_aum_with_iqeq", 0)),
        "upcoming_launch_flag": int(row.get("upcoming_launch_flag", 0)),
        "conference_engagement": round(float(row.get("conference_engagement", 0)), 4),
    }

    return AccountDetail(
        account_id=row["account_id"],
        name=row["name"],
        country=row["country"],
        segment=row["segment"],
        status=row["status"],
        key_contact=str(row.get("key_contact", "")),
        last_contact_date=row.get("last_contact_date"),
        priority_bucket=row["priority_bucket"],
        ICP_fit_score=round(float(row["ICP_fit_score"]), 4),
        buy_upsell_propensity=round(float(row["buy_upsell_propensity"]), 4),
        whitespace_flag=bool(row["whitespace_flag"]),
        upcoming_launch_flag=int(row.get("upcoming_launch_flag", 0)),
        features=features,
    )


def _repo_root() -> str:
    # data/scripts -> repo root
    return os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))


def _read_prompt(relative_path: str) -> str:
    path = os.path.join(_repo_root(), relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_json_array(text: str) -> str:
    """Robustly extract a JSON array from LLM hallucinated conversational text."""
    t = text.strip()
    # 1. Standard markdown fence parsing
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
            
    # 2. Fallback Regex extraction for raw JSON brackets hiding inside text blocks
    match = re.search(r'\[.*\]', t, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
        
    return t


def _strict_parse_prioritized_accounts(raw_text: str) -> list[PrioritizedAccount]:
    cleaned = _extract_json_array(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON output: {e.msg}") from e
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="LLM output must be a JSON array")
    try:
        return [PrioritizedAccount(**item) for item in data]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM output schema validation failed: {e}") from e


@app.post("/prioritize_accounts", response_model=PrioritizeResponse)
def prioritize_accounts(req: PrioritizeRequest):
    """
    Phase 4 orchestration: score/filter accounts, call Gemini, and return validated A/B/C + rationale.
    """
    if merged_df.empty:
        raise HTTPException(status_code=503, detail="Model artifacts not loaded.")

    # Reuse same filter semantics as /score_accounts
    df = merged_df.copy()

    if req.status_filter and req.status_filter not in {"client", "prospect"}:
        raise HTTPException(status_code=422, detail="status_filter must be client|prospect")
    if req.countries:
        df = df[df["country"].isin(req.countries)]
    if req.segments:
        df = df[df["segment"].isin(req.segments)]
    if req.status_filter:
        df = df[df["status"] == req.status_filter]
    if req.min_propensity and req.min_propensity > 0:
        df = df[df["buy_upsell_propensity"] >= req.min_propensity]

    limit = req.limit or 30
    limit = max(1, min(int(limit), 200))
    df = df.sort_values(["buy_upsell_propensity", "ICP_fit_score"], ascending=[False, False]).head(limit)

    # Grounding payload - keep only essential fields
    grounding = []
    for _, row in df.iterrows():
        grounding.append({
            "account_id": row["account_id"],
            "name": row.get("name"),
            "country": row.get("country"),
            "segment": row.get("segment"),
            "status": row.get("status"),
            "priority_bucket": row.get("priority_bucket"),
            "ICP_fit_score": float(row.get("ICP_fit_score", 0.0)),
            "buy_upsell_propensity": float(row.get("buy_upsell_propensity", 0.0)),
            "whitespace_flag": bool(row.get("whitespace_flag", False)),
            "upcoming_launch_flag": bool(row.get("upcoming_launch_flag", False)),
            "last_contact_date": row.get("last_contact_date"),
            "features": {
                "historic_win_rate": float(row.get("historic_win_rate", 0.0)),
                "avg_deal_size_eur": float(row.get("avg_deal_size_eur", 0.0)),
                "opp_count": float(row.get("opp_count", 0.0)),
                "revenue_concentration": float(row.get("revenue_concentration", 0.0)),
                "yoy_revenue_growth": float(row.get("yoy_revenue_growth", 0.0)),
                "service_penetration_score": float(row.get("service_penetration_score", 0.0)),
                "existing_middle_office_flag": bool(row.get("existing_middle_office_flag", False)),
                "esg_policy_support_flag": bool(row.get("esg_policy_support_flag", False)),
                "total_fund_aum": float(row.get("total_fund_aum", 0.0)),
                "current_aum_with_iqeq": float(row.get("current_aum_with_iqeq", 0.0)),
                "conference_engagement": float(row.get("conference_engagement", 0.0)),
            }
        })

    system_prompt = _read_prompt("documents/prompts/phase4_system.md")
    user_template = _read_prompt("documents/prompts/phase4_user_template.md")
    user_prompt = user_template.replace("{{SCORED_ACCOUNTS_JSON}}", json.dumps(grounding, ensure_ascii=False))

    try:
        raw = generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_output_tokens=8192,
        )
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    parsed = _strict_parse_prioritized_accounts(raw)

    # Validate: only account_ids from input; buckets constrained
    valid_ids = set(df["account_id"].tolist())
    for item in parsed:
        if item.account_id not in valid_ids:
            raise HTTPException(status_code=502, detail=f"LLM returned unknown account_id: {item.account_id}")
        if item.priority_bucket not in {"A", "B", "C"}:
            raise HTTPException(status_code=502, detail=f"Invalid priority_bucket for {item.account_id}: {item.priority_bucket}")
        if not (1 <= len(item.rationale_text.strip()) <= 400):
            raise HTTPException(status_code=502, detail=f"Invalid rationale_text length for {item.account_id}")

    generated_at = datetime.now(timezone.utc).isoformat()
    llm_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    return PrioritizeResponse(
        prompt_version=req.prompt_version or "v1",
        llm_provider="gemini",
        llm_model=llm_model,
        generated_at_utc=generated_at,
        results=parsed,
    )


# ── Phase 5: Audit Override Endpoints ─────────────────────────────────────────

@app.post("/overrides", response_model=OverrideRecord)
def create_override(req: OverrideRequest):
    """
    Record a human override of an LLM prioritisation result.
    Requires a forced failure categorisation per ISO 42001.
    """
    if req.failure_category not in _VALID_FAILURE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"failure_category must be one of: {', '.join(sorted(_VALID_FAILURE_CATEGORIES))}",
        )
    if req.field_changed not in _VALID_FIELDS_CHANGED:
        raise HTTPException(
            status_code=422,
            detail=f"field_changed must be one of: {', '.join(sorted(_VALID_FIELDS_CHANGED))}",
        )
    # Verify account exists
    if not merged_df.empty and req.account_id not in merged_df["account_id"].values:
        raise HTTPException(status_code=404, detail=f"Account {req.account_id} not found.")

    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_overrides (timestamp, user, account_id, field_changed, old_value, new_value, failure_category, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, req.user, req.account_id, req.field_changed, req.old_value, req.new_value, req.failure_category, req.notes),
        )
        conn.commit()
        row_id = cursor.lastrowid

    return OverrideRecord(
        id=row_id,
        timestamp=ts,
        user=req.user,
        account_id=req.account_id,
        field_changed=req.field_changed,
        old_value=req.old_value,
        new_value=req.new_value,
        failure_category=req.failure_category,
        notes=req.notes,
    )


@app.get("/overrides", response_model=list[OverrideRecord])
def list_overrides(
    account_id: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
):
    """Return all audit override records, newest first."""
    query = "SELECT id, timestamp, user, account_id, field_changed, old_value, new_value, failure_category, notes FROM audit_overrides"
    conditions = []
    params: list = []
    if account_id:
        conditions.append("account_id = ?")
        params.append(account_id)
    if failure_category:
        conditions.append("failure_category = ?")
        params.append(failure_category)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    return [
        OverrideRecord(
            id=r["id"],
            timestamp=r["timestamp"],
            user=r["user"],
            account_id=r["account_id"],
            field_changed=r["field_changed"],
            old_value=r["old_value"],
            new_value=r["new_value"],
            failure_category=r["failure_category"],
            notes=r["notes"],
        )
        for r in rows
    ]


@app.get("/overrides/summary", response_model=OverrideSummary)
def overrides_summary():
    """Aggregated override counts for the audit dashboard."""
    with sqlite3.connect(DB_PATH) as conn:
        by_cat = {}
        for row in conn.execute("SELECT failure_category, COUNT(*) FROM audit_overrides GROUP BY failure_category"):
            by_cat[row[0]] = row[1]
        by_field = {}
        for row in conn.execute("SELECT field_changed, COUNT(*) FROM audit_overrides GROUP BY field_changed"):
            by_field[row[0]] = row[1]
        total = conn.execute("SELECT COUNT(*) FROM audit_overrides").fetchone()[0]

    return OverrideSummary(by_category=by_cat, by_field=by_field, total=total)


@app.get("/metadata/countries", response_model=list[str])
def get_countries():
    """Returns a list of distinct available countries in the dataset."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT DISTINCT country FROM accounts WHERE country IS NOT NULL").fetchall()
        return [row[0] for row in rows]


# ── Phase 5: Copilot Endpoint ─────────────────────────────────────────────────

@app.post("/copilot/ask", response_model=CopilotResponse)
def copilot_ask(req: CopilotRequest):
    """Answers natural language questions using injected DB context."""
    if merged_df.empty:
        raise HTTPException(status_code=503, detail="Model artifacts not loaded.")

    # 1. Gather Context (Top 100 accounts to save tokens, plus recent overrides)
    accounts_context = merged_df.head(100).to_dict(orient="records")
    
    overrides_context = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT * FROM audit_overrides ORDER BY id DESC LIMIT 50").fetchall()
            for r in rows:
                overrides_context.append({
                    "id": r[0], "timestamp": r[1], "user": r[2], "account_id": r[3],
                    "field_changed": r[4], "old_value": r[5], "new_value": r[6],
                    "failure_category": r[7], "notes": r[8]
                })
    except Exception:
        pass

    live_data = {
        "accounts": accounts_context,
        "recent_audit_overrides": overrides_context
    }

    system_prompt = _read_prompt("documents/prompts/copilot_system_prompt.md")
    system_prompt = system_prompt.replace("{{LIVE_SYSTEM_DATA}}", json.dumps(live_data, ensure_ascii=False))

    try:
        reply = generate_text(
            system_prompt=system_prompt,
            user_prompt=req.message,
            temperature=0.2,
            max_output_tokens=8192,
        )
        return CopilotResponse(reply=reply)
    except GeminiError as e:
        error_msg = str(e).lower()
        if "token" in error_msg or "payload too large" in error_msg or "json decode error" in error_msg:
            # Custom token exhausted indicator requested by user
            raise HTTPException(
                status_code=413, 
                detail="[TOKEN EXHAUSTION ERROR] The data context or generated response exceeded the maximum allowed tokens for this model. Please ask a more specific question."
            )
        raise HTTPException(status_code=502, detail=str(e)) from e


# ── Serve frontend ────────────────────────────────────────────────────────────

_FRONTEND_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "..", "frontend"))
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/ui", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
    print(f"Frontend served at /ui from {_FRONTEND_DIR}")


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/ui/index.html")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("scoring_api:app", host="0.0.0.0", port=8000, reload=True)
