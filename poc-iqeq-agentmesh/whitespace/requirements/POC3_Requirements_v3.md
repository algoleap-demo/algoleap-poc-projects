# POC3 — Whitespace Analysis Agent
## Agentic Rapid Prototype — Requirements v3.0

| Field | Details |
|---|---|
| Document Type | POC Requirements Specification — Rapid Prototype |
| Version | 3.0 — April 2026 |
| Status | Approved for Implementation |
| Prepared By | AI Architecture Team |
| Classification | Confidential — Internal Use Only |
| Supersedes | v2.0 |
| Builds On | POC1 v3 (data backbone, propensity pickle) + POC2 v3 (account_product_matrix, product_catalog) |
| Key Changes v3 | Planner Agent removed; Orchestration Agent handles planning (linear pipeline, consistent with POC1/POC2 v3). LLM provider locked to **OpenRouter** via multi-provider router. Copilot UX deferred to Phase 2. Country-level whitespace clustering added. Shared training (2,500 accounts) and runtime (50 accounts) aligned with POC1/POC2. All thresholds, formulas, prompts, and stub strategies locked. |

---

## 01 Overview

This document defines the **rapid prototype** of the IQ-EQ Whitespace Analysis Agent for Continental Europe FAM/PIAO. The system identifies product/service gaps by account, country, and segment, producing:

- **Whitespace grid:** country × product heatmap of `ws_intensity` values
- **Top accounts:** ranked by `total_ws_potential_eur`
- **Campaign briefs:** LLM-generated messaging per whitespace cluster
- **CSV export:** top 50 whitespace cells for sales ops review

The Whitespace Agent **builds directly on POC1 and POC2**, reusing their data backbone, the account-product matrix, and the product catalog. The pipeline uses **six agents total** — one Orchestration Agent plus five specialist agents in a linear pipeline. Consistent with POC1/POC2 v3, there is no separate Planner Agent.

**The prototype is designed to:**
- Identify product/service gaps per account, country, and segment
- Rank whitespace opportunities by expected revenue potential
- Cluster high-priority whitespace into targetable campaigns
- Generate LLM-driven campaign briefs for the top 3 clusters
- Produce structured JSON and CSV outputs for sales ops
- Deliver all outputs through the Orchestration Agent directly to the user (no Copilot in prototype)

**Out of scope for this prototype:** Copilot UX layer, interactive heatmap visualisations, real CRM/Snowflake connectors, Governance Workbench UI, threshold tuning UI, authentication, persistence.

---

## 02 Objectives

- Identify product/service gaps using deterministic rules over the account-product matrix
- Rank whitespace opportunities by `ws_score` combining expected revenue, expansion potential, and strategic priority
- Cluster accounts into targetable campaign groups using k-means
- Generate LLM-driven campaign briefs (objectives, messaging angle, CTA) for the top 3 clusters
- Produce a country × product heatmap matrix for sales leadership review
- Support ISO 42001 auditability with structured logging and versioned scoring formulas

---

## 03 Agent Definitions

The pipeline uses **six agents total** in a linear flow: Orchestration → Data → Whitespace Scoring → Clustering → Campaign Brief (LLM) → Validation → Formatting → Orchestration → User.

> **Note:** POC3 has seven logical stages but six agent *components* — Clustering is deterministic and folded into the Whitespace Scoring Agent. The sequence below reflects the actual agent count.

### 03.1 Orchestration Agent

| Field | Detail |
|---|---|
| Responsibility | Receives user query, generates `pipeline_run_id`, delegates to Data Agent, receives final payload from Formatting Agent, delivers response to user |
| Input | Query parameters: country list, segment filter, product filter (optional) |
| Output | Structured whitespace payload (grid + top accounts + campaign briefs + CSV path) |
| Audit | Writes pipeline start/end events to `logs/audit.jsonl` |

### 03.2 Data Agent

| Field | Detail |
|---|---|
| Responsibility | Loads and joins POC1 data backbone + POC2/POC3 product files. Validates referential integrity. First agent in the pipeline. |
| Input Filters | country · segment · product_id list (optional) |
| Data Sources | **POC1 reuse:** accounts · opportunities · snowflake_metrics · external_funds · conferences · conference_attendance. **POC2/POC3 shared:** account_product_matrix · product_catalog. **POC3-specific:** none — all data is reused |
| Output | Validated raw dataset (multi-table dict) — clean, no orphaned FKs |
| Returns To | Whitespace Scoring Agent |
| LLM | None — deterministic data loader |

### 03.3 Whitespace Scoring Agent

| Field | Detail |
|---|---|
| Responsibility | Computes per-cell whitespace scores, per-account totals, per-country aggregates, and k-means campaign clusters. Also loads POC1's XGBoost pickle for propensity context used in conflict detection. |
| Input | Validated raw dataset from Data Agent |
| Key Formulas | `whitespace_flag(a,p) = 1 if has_product=false AND potential_revenue_bucket ∈ {Medium, High}` · `expected_revenue_eur = {Low: 50K, Medium: 150K, High: 300K}` · `ws_score(a,p) = 0.5 × norm(expected_rev) + 0.3 × expansion_weight(p) + 0.2 × strategic_priority_flag(a)` · `total_ws_potential(account) = Σ expected_rev × whitespace_flag` · `ws_intensity(account) = total_ws_potential / max(total_ws_potential)` |
| Clustering | K-means on account whitespace vectors (each vector is length 8 — one dimension per product), `k=5` fixed. Each account assigned to exactly one cluster. |
| Output Fields | Per cell: `whitespace_flag`, `expected_revenue_eur`, `ws_score`. Per account: `total_ws_potential_eur`, `ws_intensity`, `cluster_id`. Per country-product: `total_ws_potential_eur`. |
| Design Rationale | Deterministic scoring + deterministic clustering — no LLM. Reproducible, auditable, fast. |
| Returns To | Campaign Brief Agent |

### 03.4 Campaign Brief Agent (LLM)

| Field | Detail |
|---|---|
| Responsibility | Generates campaign briefs for the top 3 whitespace clusters (ranked by cluster total potential). This is the only LLM-calling agent in POC3. |
| Input | Cluster metadata: cluster_id, member accounts (account_id list), dominant products, cluster_total_potential_eur, dominant_country, dominant_segment |
| Output Fields | Per top-3 cluster: `campaign_brief_text`, `messaging_angle`, `target_account_count`, `primary_cta` |
| LLM Provider | **OpenRouter** via the multi-provider router in `agentic-ai-blueprint`. Default model configurable via env var `POC3_LLM_MODEL`. |
| LLM Constraint | Must NOT recalculate scores or invent account lists. All cluster membership comes from structured input. |
| Returns To | Validation Agent |

### 03.5 Validation Agent

| Field | Detail |
|---|---|
| Responsibility | Checks consistency of whitespace recommendations. Flags anomalies for human review. |
| Conflict Rules | `ws_score ≥ 0.7 AND product.expansion_potential == "Low"` → review flag · `campaign_cluster targets account outside product.region_fit` → warning flag · `propensity_score ≤ 0.3 AND ws_score ≥ 0.7` → review flag (big opportunity, low intent) |
| Output Fields | `validation_flags` (array per account-product: `{account_id, product_id, flag_type, anomaly_note}`) |
| ISO 42001 Hook | Flagged records appended to `logs/governance_queue.jsonl` |
| Returns To | Formatting Agent |
| LLM | None — deterministic rule check |

### 03.6 Formatting Agent

| Field | Detail |
|---|---|
| Responsibility | (1) Assemble the country × product heatmap matrix. (2) Build the top_accounts ranked list. (3) Write the top-50 CSV export. (4) Validate via Pydantic. (5) Return to Orchestration Agent. |
| Output Schema | `whitespace_grid` (2D matrix) · `top_accounts` (array) · `campaign_briefs` (top-3 array) · `validation_flags` (array) · `total_potential_eur` (float) · `export_csv_path` (string) |
| CSV Export | Top 50 whitespace cells by `ws_score`: account_id, product_id, product_line, country, expected_rev_eur, ws_score, cluster_id |
| Validation | Pydantic schema-enforced — rejects malformed payloads |
| Returns To | Orchestration Agent → user response |
| LLM | None — deterministic assembly |

---

## 04 Data Requirements

POC3 uses the POC1 data backbone plus the POC2 product files. No POC3-specific files are added — the shared `product_catalog.csv` and `account_product_matrix.csv` from POC2 are sufficient.

### 04.1 Dataset Sizing

Consistent with POC1 and POC2 v3:

| Dataset | Accounts | Purpose | Storage |
|---|---|---|---|
| Training | 2,500 | Reuses POC1 pickle and POC2 product files — no separate training | `data/training/` (gitignored) |
| Runtime/Demo | 50 | Live pipeline execution and show-and-tell | `data/synthetic/` (committed) |

**ID range convention:** same as POC1/POC2 — runtime uses `ACME-EU-90001` to `ACME-EU-90050`. POC3 inherits the golden-path account `ACME-EU-90001`.

**POC3 does not retrain anything.** It loads POC1's pickle (for propensity context in Validation) and applies deterministic formulas for whitespace scoring and k-means clustering.

### 04.2 File Summary (all reused from POC1 and POC2)

| File | Origin | Cardinality | Training Rows | Runtime Rows |
|---|---|---|---|---|
| accounts.csv | POC1 | 1:1 | 2,500 | 50 |
| opportunities.csv | POC1 | 1:N (4/account) | 10,000 | 200 |
| snowflake_metrics.csv | POC1 | 1:1 | 2,500 | 50 |
| external_funds.csv | POC1 | 1:N | ~1,500 | ~30 |
| conferences.csv | POC1 | catalog | ~25 | ~25 |
| conference_attendance.csv | POC1 | M:N | ~6,250 | ~125 |
| product_catalog.csv | POC2 (shared) | catalog | 8 | 8 |
| account_product_matrix.csv | POC2 (shared) | M:N | ~20,000 | ~400 |
| **Total raw rows** | | | **~42,800** | **~850** |

POC3 does not add files. This is deliberate — the product matrix is already sufficient for whitespace analysis.

### 04.3 Product Catalog (reused from POC2)

Same 8 products across both datasets:

| product_id | product_line | asset_class_fit | expansion_potential |
|---|---|---|---|
| PROD-01 | Fund Admin | Mixed | Low |
| PROD-02 | Middle Office | PE, RE | High |
| PROD-03 | ESG Reporting | Mixed | High |
| PROD-04 | AIFMD | PE, Hedge | Medium |
| PROD-05 | Depositary | PE, RE | Medium |
| PROD-06 | Tax Services | Private Client | Medium |
| PROD-07 | Private Client | Private Client | Low |
| PROD-08 | Transfer Agency | Mixed | Low |

**Why only 8 products in the prototype:** enough to produce a meaningful 5-cluster k-means, small enough to fit the heatmap on one screen during demo, and aligned with the 8 feature columns in POC1's trained model.

### 04.4 Engineered Demo Whitespace Patterns

Inherited from POC1 runtime accounts. POC3 adds these specific product-matrix engineering rules for the demo narrative:

| Pattern | Count | Purpose |
|---|---|---|
| Golden path (`ACME-EU-90001`) | 1 | Owns 3 products, 5 high-potential whitespace cells including ESG Reporting and Middle Office → lands in top campaign cluster |
| Cluster-forming accounts | ~15 | Similar product gap profiles → cluster together cleanly, making k-means output interpretable |
| Region mismatch accounts | 2 | Have high `ws_score` for products outside their `region_fit` → force `validation_flag=True` for the "outside region" rule |
| Saturated accounts (Bucket C background) | 5 | Own 7 of 8 products → minimal whitespace, low ws_score |
| Background | 27 | Natural distribution across products and countries |

Total: 50 runtime accounts (same set as POC1 and POC2).

---

## 05 Feature Engineering

POC3 uses deterministic formulas only — no aggregation pipeline like POC1's `features.py` is needed because whitespace scoring operates directly on the account-product matrix (which is already 1:1 at the cell level).

### 05.1 Whitespace Formulas (locked)

```python
# constants.py
EXPECTED_REVENUE_MAP = {"Low": 50_000, "Medium": 150_000, "High": 300_000}

EXPANSION_WEIGHT = {"Low": 0.3, "Medium": 0.6, "High": 1.0}

WS_SCORE_WEIGHTS = {"revenue": 0.5, "expansion": 0.3, "strategic": 0.2}

WS_HIGH_THRESHOLD = 0.7   # used in Validation Agent conflict rules
```

### 05.2 Per-Cell Computation

```python
def compute_ws_cell(account, product, cell) -> dict:
    if cell.has_product:
        return {"whitespace_flag": 0, "expected_revenue_eur": 0, "ws_score": 0.0}

    if cell.potential_revenue_bucket not in ("Medium", "High"):
        return {"whitespace_flag": 0, "expected_revenue_eur": 0, "ws_score": 0.0}

    expected_rev = EXPECTED_REVENUE_MAP[cell.potential_revenue_bucket]
    normalized_rev = expected_rev / 300_000  # max bucket

    ws_score = (
        WS_SCORE_WEIGHTS["revenue"]    * normalized_rev +
        WS_SCORE_WEIGHTS["expansion"]  * EXPANSION_WEIGHT[product.expansion_potential] +
        WS_SCORE_WEIGHTS["strategic"]  * float(account.strategic_priority_flag)
    )
    return {
        "whitespace_flag": 1,
        "expected_revenue_eur": expected_rev,
        "ws_score": round(ws_score, 4),
    }
```

### 05.3 Per-Account Rollup

```python
def compute_account_rollup(account_id, cells) -> dict:
    ws_cells = [c for c in cells if c["whitespace_flag"] == 1]
    total = sum(c["expected_revenue_eur"] for c in ws_cells)
    return {
        "account_id": account_id,
        "total_ws_potential_eur": total,
        "ws_cell_count": len(ws_cells),
    }
    # ws_intensity computed after all accounts rolled up, via normalization
```

### 05.4 K-Means Clustering

```python
# Each account represented as an 8-dimensional vector: [ws_score per product]
# Accounts with all zero vectors (no whitespace) are filtered out before clustering

from sklearn.cluster import KMeans

vectors = build_account_vectors(accounts, matrix)  # shape: (n_accounts_with_ws, 8)
km = KMeans(n_clusters=5, random_state=42, n_init=10)
labels = km.fit_predict(vectors)
```

**Cluster selection for LLM briefing:** after clustering, rank clusters by `sum(total_ws_potential_eur)` across their member accounts. The **top 3 clusters by total potential** are passed to the Campaign Brief Agent.

---

## 06 Decision Rules

### 06.1 Validation Rules (Validation Agent)

```python
def validate_cell(account, product, cell_score, propensity_score) -> list[dict]:
    flags = []

    if cell_score["ws_score"] >= WS_HIGH_THRESHOLD \
       and product.expansion_potential == "Low":
        flags.append({
            "flag_type": "review",
            "anomaly_note": "High ws_score on a Low expansion_potential product — review scoring weights",
        })

    if cell_score["whitespace_flag"] == 1 \
       and account.country not in product.region_fit.split(","):
        flags.append({
            "flag_type": "warning",
            "anomaly_note": f"Product {product.product_id} region_fit does not include {account.country}",
        })

    if propensity_score <= 0.3 and cell_score["ws_score"] >= WS_HIGH_THRESHOLD:
        flags.append({
            "flag_type": "review",
            "anomaly_note": "Large whitespace opportunity but low buying intent — review targeting",
        })

    return flags
```

### 06.2 Campaign Brief Agent Prompt (locked starting point)

```
You are the Campaign Brief Agent for IQ-EQ FAM/PIAO whitespace analysis.

Given the following cluster:
- cluster_id: {cluster_id}
- member_accounts: {account_id_list} (count: {n})
- dominant_products: {top_2_products_by_ws_score}
- cluster_total_potential_eur: {total}
- dominant_country: {country}
- dominant_segment: FAM or PIAO
- representative account profile: {avg_fund_size_eur, avg_relationship_depth}

Produce a campaign brief with exactly these sections:
1. messaging_angle (one sentence — the hook that unites this cluster)
2. objectives (3 bullets)
3. suggested_sequence (4 bullets — outreach sequence)
4. primary_cta (one short call-to-action)

Constraints:
- Do NOT invent account IDs. Only reference the provided member_accounts if needed.
- Do NOT invent product names outside dominant_products.
- Focus on commercial rationale, not technical product details.
- Total brief under 300 words.

Return strict JSON: {
  "messaging_angle": "...",
  "campaign_brief_text": "...",
  "primary_cta": "..."
}
```

### 06.3 No NBA Resolution

POC3 does not produce per-account NBA actions. NBA resolution is POC2's responsibility. POC3's primary output is **cluster-level campaign briefs**, not individual account actions.

---

## 07 Execution Flow

Linear pipeline. The Orchestration Agent initiates and receives. No hub-and-spoke back to a Planner.

1. User submits whitespace query (country filter + segment filter) → Orchestration Agent
2. Orchestration Agent generates `pipeline_run_id`, delegates to Data Agent
3. Data Agent loads + joins all 8 CSVs → passes validated raw dataset to Whitespace Scoring Agent
4. Whitespace Scoring Agent computes per-cell scores, per-account rollups, and k-means clusters → ranks clusters by total potential → passes top 3 clusters + full scored dataset to Campaign Brief Agent
5. Campaign Brief Agent invokes **OpenRouter** via the blueprint router → generates 3 campaign briefs (one per top cluster) → passes to Validation Agent
6. Validation Agent applies rule checks → flagged records appended to `logs/governance_queue.jsonl` → passes to Formatting Agent
7. Formatting Agent assembles the heatmap grid, top_accounts list, campaign briefs array, writes CSV export, validates via Pydantic → returns to Orchestration Agent
8. Orchestration Agent delivers final response directly to user

---

## 08 Output Schema

```json
{
  "pipeline_run_id": "uuid4",
  "generated_at": "2026-04-08T12:34:56Z",
  "model_version": "poc3_v1+router_v1",
  "total_potential_eur": 12500000,
  "whitespace_grid": {
    "countries": ["DE", "FR", "IT", "ES", "NL", "BE", "CH", "LU"],
    "products": ["PROD-01", "PROD-02", "PROD-03", "PROD-04", "PROD-05", "PROD-06", "PROD-07", "PROD-08"],
    "intensity_matrix": [[0.2, 0.8, 0.9, 0.3, 0.4, 0.5, 0.1, 0.2], "..."]
  },
  "top_accounts": [
    {
      "account_id": "ACME-EU-90001",
      "total_ws_potential_eur": 750000,
      "ws_intensity": 0.92,
      "top_products": ["PROD-03", "PROD-02"],
      "cluster_id": 2
    }
  ],
  "campaign_briefs": [
    {
      "cluster_id": 2,
      "target_account_count": 12,
      "cluster_total_potential_eur": 3600000,
      "dominant_country": "DE",
      "dominant_products": ["ESG Reporting", "Middle Office"],
      "messaging_angle": "German PE firms face mounting SFDR pressure — we can close the ESG reporting gap and layer in Middle Office efficiency in one engagement.",
      "campaign_brief_text": "**Objectives**\n- Secure 6 ESG Reporting wins by Q3...\n...",
      "primary_cta": "Book a 30-min ESG readiness assessment"
    }
  ],
  "validation_flags": [
    {
      "account_id": "ACME-EU-90012",
      "product_id": "PROD-07",
      "flag_type": "warning",
      "anomaly_note": "Product PROD-07 region_fit does not include IT"
    }
  ],
  "export_csv_path": "outputs/whitespace_top50_<run_id>.csv"
}
```

---

## 09 API Surface

The prototype exposes a **single endpoint**. Other endpoints from the v2 spec (`/whitespace_by_account`, `/whitespace_by_product_country`, `/campaign_brief`, `/whitespace_export`) are not built — their functionality is consolidated into the single endpoint's response.

| Endpoint | Method | Description |
|---|---|---|
| `/analyze_whitespace` | POST | Trigger full pipeline with filters in payload (country list, segment). Returns the structured whitespace payload including grid, top accounts, campaign briefs, and CSV export path. |

---

## 10 Stub Strategy

| Component | Prototype Stub |
|---|---|
| Copilot UX | Not built — JSON response only |
| Interactive heatmap | Not built — heatmap data returned as matrix, user renders externally (e.g., paste into Excel) |
| Threshold tuning UI | Not built — thresholds in `constants.py`, requires code change to modify |
| Governance Workbench | Append flagged records to `logs/governance_queue.jsonl` |
| Audit log | `logs/audit.jsonl` — one line per agent invocation |
| Override mechanism | Out of scope |
| Error handling | Fail loudly with structured exception; no retries |
| Auth / RBAC | None |
| Persistence | None — stateless per request |

---

## 11 Project Layout

POC3 lives alongside POC1 and POC2 in a shared monorepo structure:

```
poc3-whitespace/
├── app/
│   ├── main.py                  # FastAPI entry, POST /analyze_whitespace
│   ├── orchestration_agent.py
│   ├── agents/
│   │   ├── data_agent.py
│   │   ├── whitespace_scoring_agent.py   # scoring + k-means clustering
│   │   ├── campaign_brief_agent.py       # LLM via OpenRouter
│   │   ├── validation_agent.py
│   │   └── formatting_agent.py
│   ├── scoring.py               # compute_ws_cell, compute_account_rollup
│   ├── clustering.py            # k-means wrapper with fixed seed
│   ├── schemas.py               # pydantic models
│   └── constants.py             # thresholds, weight maps, k=5
├── data/
│   ├── training/                # gitignored — symlinked from POC1/POC2
│   └── synthetic/               # committed — symlinked from POC1/POC2
├── models/
│   └── xgb_propensity_v1.pkl    # symlinked from POC1 (used in Validation)
├── outputs/                     # runtime CSV exports (gitignored)
├── scripts/
│   └── regenerate_runtime_data.sh   # re-runs POC2 generators for matrix updates
├── logs/
├── tests/
│   ├── test_ws_score_bounds.py      # ws_score ∈ [0, 1] for all cells
│   ├── test_cluster_count.py        # k=5 clusters always produced
│   └── test_golden_path_poc3.py     # ACME-EU-90001 in top cluster
├── .env.example                 # OPENROUTER_API_KEY, POC3_LLM_MODEL
└── README.md
```

**Critical:** POC3 does NOT generate its own data. It depends on POC1's data backbone and POC2's product files. Generators live in POC1 and POC2 repos; POC3 only reads.

---

## 12 LLM Provider: OpenRouter

POC3 uses **OpenRouter** as the LLM gateway, identical to POC2. All LLM calls in the Campaign Brief Agent route through the multi-provider router in `agentic-ai-blueprint`.

### 12.1 Why OpenRouter

- Consistent with POC2 — same router, same config pattern, one LLM gateway for all POCs
- Single API surface for multiple model providers
- Graceful fallback if one provider is degraded
- Unified cost tracking across all three POCs
- Matches the `agentic-ai-blueprint` multi-provider router pattern — no custom SDK code

### 12.2 Configuration

```python
# .env
OPENROUTER_API_KEY=sk-or-v1-...
POC3_LLM_MODEL=anthropic/claude-3.5-sonnet  # configurable
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# app/agents/campaign_brief_agent.py
from blueprint.router import LLMRouter

router = LLMRouter(
    provider="openrouter",
    api_key=os.environ["OPENROUTER_API_KEY"],
    model=os.environ.get("POC3_LLM_MODEL", "anthropic/claude-3.5-sonnet"),
    base_url=os.environ["OPENROUTER_BASE_URL"],
)

response = router.complete(
    system_prompt=CAMPAIGN_BRIEF_SYSTEM_PROMPT,
    user_prompt=render_cluster_context(cluster),
    response_format="json",
    temperature=0.3,   # slightly higher than POC2 for creative messaging angles
    max_tokens=800,
)
```

### 12.3 Model Selection Guidance

Same as POC2:

| Use case | Recommended OpenRouter model |
|---|---|
| Default (balanced cost/quality) | `anthropic/claude-3.5-sonnet` |
| Budget-conscious demo runs | `openai/gpt-4o-mini` |
| Creative messaging angles | `anthropic/claude-3.5-sonnet` (better at marketing copy) |
| Local/offline testing | `meta-llama/llama-3.1-70b-instruct` |

**Only 3 LLM calls per run** (one per top cluster), so model cost is negligible — the default choice can be the highest-quality model without budget concerns.

### 12.4 Production Path

In Phase 2, OpenRouter will be replaced with the internal **IQEQ.AI** tenant. Identical to POC2, this is a one-file change in `agentic-ai-blueprint`.

---

## 13 Constraints

| Constraint | Description |
|---|---|
| Single LLM agent | Only the Campaign Brief Agent calls an LLM. All other agents deterministic. |
| Only 3 LLM calls per run | One per top-3 cluster. No per-account LLM calls. |
| No data generation | POC3 reads data produced by POC1/POC2 generators — never generates its own |
| Reproducible clustering | K-means uses fixed `random_state=42` and `n_init=10` for deterministic output |
| Structured outputs only | All agent outputs conform to Pydantic schema |
| No NBA actions | NBA is POC2's responsibility — POC3 outputs cluster-level briefs only |
| Scoring formula versioned | `ws_score` weights (0.5 / 0.3 / 0.2) are documented and committed to `constants.py` |
| LLM provider locked | OpenRouter only |
| Data privacy | 100% synthetic |

---

## 14 Definition of Done

- [ ] POC3 reads training and runtime data successfully from POC1/POC2 directories
- [ ] `test_ws_score_bounds.py` passes — `ws_score ∈ [0, 1]` for every whitespace cell
- [ ] `test_cluster_count.py` passes — k-means always produces exactly 5 clusters with at least 1 account each
- [ ] `POST /analyze_whitespace` returns valid JSON for the default runtime filter
- [ ] `whitespace_grid` matrix has shape (8 countries × 8 products) with values in [0, 1]
- [ ] `top_accounts` is a ranked list with ACME-EU-90001 in the top 5
- [ ] Exactly 3 campaign briefs generated per run, one per top-3 cluster
- [ ] Golden-path account `ACME-EU-90001` is in one of the top 3 clusters
- [ ] CSV export at `outputs/whitespace_top50_<run_id>.csv` contains exactly 50 rows
- [ ] At least 1 region-mismatch validation flag raised for the engineered mismatch accounts
- [ ] `logs/audit.jsonl` contains one entry per agent per run
- [ ] `logs/governance_queue.jsonl` contains the flagged records
- [ ] OpenRouter integration works with at least 2 different models (env var swap)
- [ ] Pydantic schema validation rejects malformed payloads (one negative test)
- [ ] README documents OpenRouter setup and model swapping

---

## 15 Future Enhancements (Phase 2+)

| Enhancement | Description | Phase |
|---|---|---|
| Copilot UX Layer | Interactive heatmap + cluster drill-down in Copilot | Phase 2 |
| Threshold Tuning UI | Sales ops adjusts scoring weights and regenerates views without code changes | Phase 2 |
| IQEQ.AI Model Swap | Replace OpenRouter with internal IQEQ.AI tenant | Phase 2 |
| Production Data Bridge | Live Snowflake + CRM connectors replacing synthetic CSVs | Phase 2 |
| Real-time Cluster Monitoring | POC3 output feeds POC1 Orchestration for continuous whitespace tracking | Phase 2 |
| Dynamic K | Auto-select k via silhouette score instead of fixed k=5 | Phase 2 |
| ML Ranking Layer | Replace deterministic ws_score with a learned ranker trained on historical conversions | Phase 2 |
| Campaign Execution | Auto-push campaign briefs into marketing automation platforms | Phase 3 |
| Cross-POC Orchestration | POC1 → POC2 → POC3 as a unified intelligence pipeline | Phase 3 |

---

## 16 Open Questions Parked for v2 Spec

1. Is k=5 clusters right for production, or should it scale with dataset size?
2. Should clustering use ws_score vectors or expected_revenue vectors (current: ws_score)?
3. Should campaign briefs be per-cluster or per-(cluster × country) to get more specific messaging?
4. Threshold for `WS_HIGH_THRESHOLD` (currently 0.7) — needs sales ops input
5. Should `total_potential_eur` be weighted by account propensity, or pure whitespace?
6. Region mismatch rule: soft warning or hard block?
7. Confidence thresholds for publishing campaigns without human review?
8. Should the validation agent check for propensity-whitespace conflicts, overlapping with POC2's validation logic?
