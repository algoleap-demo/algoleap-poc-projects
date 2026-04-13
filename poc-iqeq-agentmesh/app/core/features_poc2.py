"""POC2 account-planning features: contact influence, relationship depth, role/seniority inference."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

import pandas as pd

from app.core.constants import (
    API_SCORE_WEIGHTS,
    EXPECTED_REVENUE_MAP,
    ROLE_WEIGHTS,
    SENIORITY_WEIGHTS,
)


def _norm_clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def infer_role_bucket(role: str) -> str:
    """Map free-text CRM role labels to ROLE_WEIGHTS keys."""
    if not isinstance(role, str) or not role.strip():
        return "Other"
    rl = role.lower()
    if re.search(r"\bchief executive\b|\bceo\b", rl):
        return "CEO"
    if re.search(r"\bchief financial\b|\bcfo\b", rl):
        return "CFO"
    if re.search(r"\bchief operating\b|\bcoo\b", rl):
        return "COO"
    if "head of fund" in rl or "head of ops" in rl or "operations" in rl:
        return "Head of Ops"
    if "portfolio" in rl:
        return "Portfolio Manager"
    if "compliance" in rl or "counsel" in rl or "legal" in rl:
        return "Compliance"
    if "it" == rl or "technology" in rl or "cio" in rl:
        return "IT"
    return "Other"


def infer_seniority(role: str) -> str:
    rl = (role or "").lower()
    if re.search(r"\bchief\b|\bceo\b|\bcfo\b|\bcoo\b|\bcio\b", rl):
        return "C-Level"
    if "vp" in rl or "vice president" in rl:
        return "VP"
    if "director" in rl or "head of" in rl:
        return "Director"
    if "manager" in rl:
        return "Manager"
    return "Individual Contributor"


def contact_influence(role: str, seniority: str, engagement: float) -> float:
    rb = infer_role_bucket(role)
    sw = SENIORITY_WEIGHTS.get(seniority, SENIORITY_WEIGHTS["Manager"])
    rw = ROLE_WEIGHTS.get(rb, ROLE_WEIGHTS["Other"])
    return float(rw * sw * engagement)


def relationship_depth(account_id: str, raw: Dict[str, pd.DataFrame]) -> float:
    """§05.1: 0.4*norm(contacts) + 0.3*avg(engagement) + 0.3*norm(opps)."""
    contacts = raw["contacts"][raw["contacts"].account_id == account_id]
    opps = raw["opportunities"][raw["opportunities"].account_id == account_id]
    n_ct = len(contacts)
    n_norm = _norm_clip(n_ct / 5.0)

    if "engagement_score" in contacts.columns and not contacts.empty:
        eng = float(contacts["engagement_score"].astype(float).mean())
    else:
        eng = 0.55 if n_ct else 0.0

    n_op = len(opps)
    op_norm = _norm_clip(n_op / 10.0)
    return float(0.4 * n_norm + 0.3 * _norm_clip(eng) + 0.3 * op_norm)


def top_contacts_for_account(
    account_id: str, raw: Dict[str, pd.DataFrame], k: int = 3
) -> List[Dict[str, Any]]:
    contacts = raw["contacts"][raw["contacts"].account_id == account_id]
    rows: List[Tuple[float, Dict[str, Any]]] = []
    for _, c in contacts.iterrows():
        role = str(c.get("role", "") or "")
        seniority = str(c.get("seniority", "") or "").strip() or infer_seniority(role)
        if "engagement_score" in contacts.columns:
            eng = float(c.get("engagement_score", 0.5) or 0.5)
        else:
            eng = 0.65 if c.get("is_primary") else 0.55
        inf = contact_influence(role, seniority, eng)
        name = str(c.get("full_name", c.get("name", "")) or "")
        rows.append(
            (
                inf,
                {
                    "name": name,
                    "role": role,
                    "seniority": seniority,
                    "influence_score": round(inf, 4),
                },
            )
        )
    rows.sort(key=lambda x: -x[0])
    return [r[1] for r in rows[:k]]


def normalize_ws_potentials(ws_by_account: Dict[str, float]) -> Dict[str, float]:
    """Min–max normalize total_ws_potential to [0,1] across the batch."""
    vals = list(ws_by_account.values())
    if not vals:
        return {}
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {a: 0.5 for a in ws_by_account}
    return {a: (ws_by_account[a] - lo) / (hi - lo) for a in ws_by_account}


def compute_api_score(
    propensity: float, norm_whitespace: float, strategic_flag: bool
) -> float:
    w = API_SCORE_WEIGHTS
    strat = 1.0 if strategic_flag else 0.0
    return float(
        w["propensity"] * propensity
        + w["whitespace"] * norm_whitespace
        + w["strategic"] * strat
    )


def matrix_has_product(row: pd.Series) -> bool:
    if "has_product" in row.index:
        v = row["has_product"]
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("true", "1", "yes")
    return bool(row.get("is_active", False))


def matrix_potential_bucket(row: pd.Series) -> str:
    if "potential_revenue_bucket" in row.index and pd.notna(
        row.get("potential_revenue_bucket")
    ):
        b = str(row["potential_revenue_bucket"]).strip()
        if b in EXPECTED_REVENUE_MAP:
            return b
    return "Medium"


def whitespace_flag(row: pd.Series) -> bool:
    if matrix_has_product(row):
        return False
    b = matrix_potential_bucket(row)
    return b in ("Medium", "High")
