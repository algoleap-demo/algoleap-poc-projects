Here is the completely revised Proof of Concept (POC) Requirement Document for the Targeting & Triage Agent, formatted as a Markdown (`.md# End-to-End Configured LLM POC - Targeting & Triage Agent (Synthetic IQ-EQ Data)

## 1. Overview
This document describes a complete, implementable Proof of Concept (POC) for a Configured LLM-based Targeting & Triage Agent for IQ-EQ's Continental Europe Funds & Institutional Asset Owners (FAM/PIAO) business, using fully synthetic data. 

It includes synthetic data generation prompts, data schemas, machine learning workflows, and crucial enterprise-grade safety mechanisms—including an **ISO 42001 Governance Workbench** and an **Offline Bridging Strategy**—designed specifically to align with IQ-EQ's "4B" (build, borrow, buy, bridge) security posture.

## 2. Synthetic Data Generation (Configured LLM Prompt)
Use the following master prompt in Configured LLM to generate synthetic CSV datasets. After running it, copy each CSV block into local `.csv` files.

```text
You are a data generator for a sales-ops POC for IQ-EQ's Continental Europe FAM/PIAO business.Generate five synthetic CSV datasets that are internally consistent and realistic but contain no real client data.
Datasets:
1) accounts.csv with 150 rows.
2) opportunities.csv with ~800 rows.
3) snowflake_metrics.csv with 150 rows (one per account).
4) external_funds.csv with 200 rows.
5) conferences.csv with 20 rows.

Use these schemas and constraints:
accounts.csv fields:
- account_id (string, e.g. ACC_LU_0001)
- name (e.g. Lux PE Fund I SCSp, NL Infra Fund II BV, Green Real Estate Fund SCA)
- country (LU, NL, FR, IT only)
- segment (FAM or PIAO)
- status (client or prospect)
- key_contact (synthetic email)
- iqeq_relationship_start_date (date 2017-01-01 to 2025-12-31; NULL for prospects)
- last_contact_date (date in 2025-01-01 to 2026-03-01; NULL allowed)
- associated_conference_id (one of conference_ids from conferences.csv or empty)
- strategic_priority_flag (true/false, ~40% true)

opportunities.csv fields:
- opp_id (string, e.g. OPP_000123)
- account_id (must match an account in accounts.csv)
- close_date (date 2022-01-01 to 2026-03-01)
- stage (Prospecting, Proposal, Negotiation, Closed Won, Closed Lost)
- status (won or lost; if stage is Closed Won/Lost then status must match)
- product_line (Fund Admin, AIFM, Depositary, Middle Office, ESG Reporting, Regulatory)
- deal_size_eur (number, 50,000-5,000,000; larger for PE/Infra funds)
- competitor (Competitor A/B/C or empty)
- win_loss_reason_code (e.g. PRICE, ONBOARDING_SPEED, COVERAGE, COMPETITOR_RELATIONSHIP, OTHER)
- win_loss_notes (1-2 sentence synthetic explanation)

snowflake_metrics.csv fields (one per account_id):
- account_id
- current_aum_with_iqeq (0-1,500,000,000; 0 allowed for prospects)
- total_fund_aum (100,000,000-3,000,000,000; must be >= current_aum_with_iqeq)
- revenue_fund_admin (0-600,000; 0 allowed)
- revenue_middle_office (0-400,000; 0 allowed)
- yoy_revenue_growth (-0.2 to 0.3)
- service_penetration_score (0-1)
- existing_middle_office_flag (true if revenue_middle_office>0 else false)
- esg_policy_support_flag (true/false, more likely true for 'Green'/'ESG' names)

external_funds.csv fields:
- fund_id (FUND_LU_9001 style)
- manager_name (should match or be related to some accounts.name)
- domicile (LU, NL, FR, IT)
- asset_class (PE, RE, Infra, Private Debt)
- aum_eur (100,000,000-3,000,000,000)
- next_launch_date (some NULL, some dates in 2026-2027)
- last_launch_date (some NULL, some 2022-2024)
- strategy_tags (semicolon-separated, e.g. 'Buyout; Mid-market')
- launch_region_focus (Europe, Global, Western Europe)

conferences.csv fields:
- conference_id (CONF_LUX_2025 style)
- name (e.g. IQ-EQ Lux Funds Summit 2025)
- date (2024-01-01 to 2026-03-01)
- location (city, country)
- theme (include ESG, T+1 readiness, Private Debt, etc.)
- accounts_present (semicolon-separated account_ids)
- engagement_score (0-1)

Requirements:
- Ensure foreign keys line up (opportunities.account_id and snowflake_metrics.account_id must exist in accounts.csv).
- Roughly 60% of accounts in LU/NL, 40% FR/IT.
- Mix of clients vs prospects (~60/40).
- At least 20 accounts with upcoming launches (external_funds.next_launch_date not null and in the future).

Output the five CSVs separately, each in its own fenced code block with header row and no commentary. Use comma as separator.
```

## 3. Data Schemas (Summary)
Once the synthetic CSVs are generated, you should have the following tables:
- `accounts.csv`
- `opportunities.csv`
- `snowflake_metrics.csv`
- `external_funds.csv`
- `conferences.csv`

## 4. Example Configured LLM User Queries
- For Netherlands and Luxembourg FAM/PIAO accounts, give me a prioritised list of 30 accounts for Q3 outreach, with buy/upsell propensity and whitespace flags.
- Explain why Lux PE Fund I SCSp is ranked as Priority A. What are the top three factors driving its buy/upsell propensity?
- Show me 10 high-potential prospects in the Netherlands with upcoming fund launches where IQ-EQ has no middle-office services today.

## 5. Implementation Workflow with Configured LLM

### 5.1 Offline Data & ML Steps
- Load the five synthetic CSVs into a local database or dataframes (e.g., using Python/pandas).
- Build per-account features from opportunities and snowflake metrics (e.g., historic win rate, average deal size, number of products, revenue growth, launch/event signals).
- Train a simple buy/upsell propensity model using a classical ML algorithm (e.g., logistic regression or gradient boosting) to predict probability of winning/expanding for each account.
- Save the trained model as a reusable artifact (e.g., pickle file).

### 5.2 Backend / Tooling Endpoints
Expose minimal backend functionality that Configured LLM can call:
- `POST /score_accounts`
- `GET /account_view/{account_id}`

Example response from `/score_accounts` (one account):
```json
{  
  "account_id": "ACC_LU_0001",  
  "name": "Lux PE Fund I SCSp",  
  "country": "LU",  
  "segment": "FAM",  
  "ICP_fit_score": 0.88,  
  "buy_upsell_propensity": 0.79,  
  "whitespace_flag": true,  
  "upcoming_launch_flag": true,  
  "features": {    
    "total_fund_aum": 1500000000,    
    "current_aum_with_iqeq": 750000000,    
    "service_penetration_score": 0.5,    
    "existing_middle_office_flag": false,    
    "esg_policy_support_flag": true  
  }
}
```

### 5.3 Configured LLM Orchestration Prompt (Prioritisation)
**System:** You are a sales operations assistant helping prioritise FAM/PIAO accounts in Continental Europe for IQ-EQ. You receive a list of accounts with pre-computed scores and features. Your job is to rank them, assign Priority A/B/C, and generate short rationales in plain business language. Do not recalculate scores; use them as-is.

**User:** Here is the JSON payload of scored accounts for Netherlands and Luxembourg. Return a JSON array with fields: `account_id`, `priority_bucket` (A/B/C), and `rationale_text` (1-3 sentences).

### 5.4 ISO 42001 Governance Workbench (Human-in-the-Loop)
To comply with IQ-EQ's ISO 42001 certification for responsible AI, simple text-box edits are not permitted. This POC utilizes a structured evaluation workbench:
- **Forced Categorization:** If a human user (e.g., sales ops) overrides Configured LLM's priority ranking or modifies a rationale, the UI forces them to categorize the AI's failure via a dropdown menu. Categories include: **"Policy Misalignment," "Hallucination," or "Data Latency"**.
- **ISO 42001 Dashboard Mapping:** These categorized overrides are mapped directly to a lightweight dashboard that aligns with ISO 42001 controls, providing the risk management team with real-time visibility into the agent's performance.
- **Continuous Improvement Pipeline:** The tracked data establishes an auditable loop. For example, a spike in "policy misalignment" flags alerts engineering that prompts require updated jurisdictional context, whereas "hallucination" spikes signal a failure in the retrieval pipeline.

### 5.5 Production Bridging Strategy (Offline Transition)
While this POC utilizes Configured LLM's external API for safe testing on purely synthetic data, live production at IQ-EQ requires operating behind the corporate firewall to protect the "3 Cs" (compliance, clients, and colleagues). 
To transition to the local `IQEQ.AI` infrastructure:
- The external API `POST` calls outlined in Section 5.2 will be replaced by local inferences.
- Because local models often struggle with massive context windows, the comprehensive Configured LLM system prompts will be broken down and refactored into smaller, chained prompts.

## 6. ML Feature Engineering and Algorithms

### 6.1 Per-Account Feature Formulas
- **Historic win rate:** `(number of won opportunities) / (total closed opportunities)`.
- **Average deal size:** `mean(deal_size_eur)` across all opportunities.
- **Revenue concentration:** `current_aum_with_iqeq / total_fund_aum`.
- **Upcoming launch flag:** `1` if any `external_funds.next_launch_date > today` for linked funds, else `0`.
- **Conference engagement:** `max(engagement_score)` across attended conferences.

### 6.2 Recommended Algorithms
- **Primary model:** Gradient Boosted Trees (e.g., XGBoost or LightGBM) for `buy_upsell_propensity` due to non-linear handling and feature importance metrics.
- **Baseline model:** Logistic Regression with L2 regularisation.

### 6.3 Example Python Logic (Pseudocode)
```python
# 1. Train model (e.g., XGBoost):
model = XGBClassifier(max_depth=4, n_estimators=200, learning_rate=0.05)
model.fit(X_train, y_train)

# 2. Score all accounts:
propensity = model.predict_proba(X_all)[:,1]

# 3. Normalise and bucket scores:
# High: propensity >= 0.7
# Medium: 0.4 <= propensity < 0.7
# Low: propensity < 0.4.
```
*(Sources:)*

## 7. Query Coverage and Extensions
For implementation completeness, the system can additionally output:
- A CSV-ready table of prioritised accounts with all scores and flags for direct upload into the CRM.
- Simulations demonstrating the impact of changing business rules (e.g., doubling the weight of upcoming launches) on the top 10 accounts.