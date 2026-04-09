# Targeting & Triage Agent — End-to-End POC
**Project Execution Plan | FAM/PIAO Continental Europe | Synthetic IQ-EQ Data**  
Version 1.0 | Prepared by: AI Engineering Team | Status: Active  

---

## 1. Executive Summary

This document defines the end-to-end project execution plan for the IQ-EQ Targeting & Triage Agent POC. The agent helps the Continental Europe FAM/PIAO sales operations team prioritise accounts for Q3 outreach using:

- AI-driven propensity scores  
- Whitespace analysis  
- Buy/upsell signals  

All built and validated on **synthetic data only** before production deployment.

### Key Details

| Dimension | Details | Metric | Target |
|----------|--------|--------|--------|
| Scope | LU, NL, FR, IT — FAM & PIAO segments | Accounts modelled | 150 accounts, ~800 opportunities |
| Goal | Rank accounts; assign Priority A/B/C | Model accuracy | AUC ≥ 0.75 |
| Security | External LLM API for POC | Governance | ISO 42001-aligned |
| Duration | 6 weeks | Team size | 2–3 engineers + SME + AI lead |

---

## 2. Project Milestones & Schedule

### Phase-wise Breakdown

| Phase | Task | Start | End | Owner | Status |
|------|------|------|-----|------|--------|
| Phase 1 | Generate synthetic CSV datasets | Wk1 D1 | Wk1 D2 | AI Engineer | Planned |
| Phase 1 | Validate referential integrity | Wk1 D2 | Wk1 D3 | AI Engineer | Planned |
| Phase 1 | Load into SQLite/DuckDB | Wk1 D3 | Wk1 D4 | AI Engineer | Planned |
| Phase 2 | Feature matrix creation | Wk1 D4 | Wk2 D1 | Data Engineer | Planned |
| Phase 2 | Train Logistic Regression | Wk2 D1 | Wk2 D2 | Data Engineer | Planned |
| Phase 2 | Train XGBoost model | Wk2 D2 | Wk2 D3 | Data Engineer | Planned |
| Phase 2 | Model evaluation (AUC) | Wk2 D3 | Wk2 D4 | AI Lead | Planned |
| Phase 3 | Build `/score_accounts` API | Wk2 D4 | Wk3 D2 | Backend Eng | Planned |
| Phase 3 | Build `/account_view/{id}` API | Wk3 D2 | Wk3 D3 | Backend Eng | Planned |
| Phase 3 | Integration testing | Wk3 D3 | Wk3 D4 | Backend Eng | Planned |
| Phase 4 | LLM prompt design | Wk3 D4 | Wk4 D1 | AI Lead | Planned |
| Phase 4 | Connect LLM orchestration | Wk4 D1 | Wk4 D2 | AI Engineer | Planned |
| Phase 4 | End-to-end testing | Wk4 D2 | Wk4 D3 | AI Lead + SME | Planned |
| Phase 5 | Build ISO workbench UI | Wk4 D3 | Wk5 D2 | Frontend Eng | Planned |
| Phase 5 | Audit dashboard integration | Wk5 D2 | Wk5 D3 | Backend Eng | Planned |
| Phase 5 | Offline bridging documentation | Wk5 D3 | Wk5 D4 | AI Lead | Planned |
| Phase 6 | UAT execution | Wk5 D4 | Wk6 D2 | SME | Planned |
| Phase 6 | Feedback & tuning | Wk6 D2 | Wk6 D3 | AI Engineer | Planned |
| Phase 6 | Final handover | Wk6 D3 | Wk6 D4 | AI Lead | Planned |

---

## 3. Risks & Mitigations

| Risk | Category | RAG | Mitigation | Owner |
|------|----------|-----|------------|------|
| Synthetic data unrealistic | Data Quality | AMBER | Validate vs real anonymised stats | Data Engineer |
| LLM hallucination | AI Quality | AMBER | Constrain prompt + audit workbench | AI Lead |
| API rate limits | Infrastructure | GREEN | Batch + cache + retry | Backend Eng |
| Context window limits | Architecture | AMBER | Use chained prompts | AI Lead |
| SME unavailable | Resource | GREEN | Pre-book + async feedback | Project Lead |

---

## 4. Key Deliverables

| # | Deliverable | Description | Format | Phase |
|--|------------|------------|--------|------|
| 1 | Dataset Bundle | 5 validated CSVs | CSV | Phase 1 |
| 2 | Feature Script | Feature engineering logic | Python | Phase 2 |
| 3 | ML Models | XGBoost + LR models | PKL + Report | Phase 2 |
| 4 | Scoring API | `/score_accounts`, `/account_view` | REST API | Phase 3 |
| 5 | LLM Config | Prompts + examples | Markdown/JSON | Phase 4 |
| 6 | ISO Workbench | Override UI + audit logs | React | Phase 5 |
| 7 | Bridging Doc | Migration to IQEQ.AI | Word | Phase 5 |
| 8 | UAT Report | Feedback + acceptance | Word | Phase 6 |
| 9 | Handover Package | Docs + architecture | GitHub | Phase 6 |

---

## 5. Architecture Overview

### Layers

#### Data Layer
- Synthetic CSVs (DuckDB)
- Pandas pipeline  
- **Production:** Snowflake + CRM (Salesforce/Dynamics)

#### ML Layer
- XGBoost + scikit-learn  
- Pickle serialization  
- **Production:** MLflow + retraining

#### LLM Layer
- External LLM API  
- Structured prompts  
- **Production:** IQEQ.AI + RAG

#### Governance Layer
- ISO 42001 workbench  
- Override tracking  
- **Production:** Risk management integration

---

## 6. Acceptance Criteria

| Criterion | Measurement | Threshold | Verified By |
|----------|------------|----------|-------------|
| Model performance | AUC | ≥ 0.75 | AI Lead |
| Ranking completeness | Coverage | 100% | Data Eng |
| API latency | p95 | < 2 sec | Backend Eng |
| LLM quality | SME rating | ≥ 80% | SME |
| Override logging | Accuracy | 100% | AI Lead |
| Data integrity | FK violations | 0 errors | Data Eng |

---
