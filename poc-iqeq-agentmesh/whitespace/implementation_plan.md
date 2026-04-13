# Implementation Plan — POC 3: Whitespace Analysis

## Goals
Implement a cluster-based whitespace agent that identifies strategic market gaps using deterministic k-means and LLM campaign generation.

## Phase 1: Algorithm & Data
- [ ] Import `KMeans` from Scikit-Learn.
- [ ] Implement `clustering.py` with fixed random seed (42).
- [ ] Verify access to shared `account_product_matrix.csv`.

## Phase 2: Agent Node Development
- [ ] **Scoring Agent**: Implement intensity calculations per country/product.
- [ ] **Clustering Node**: Implement k-means vectorization and labeling.
- [ ] **Campaign Agent**: Implement `LCEL` for generating messaging angles per cluster via `LLM_SEMAPHORE`.

## Phase 3: Validation & Formatting
- [ ] Implement Region Mismatch rules.
- [ ] Create the heatmap matrix generation logic.
- [ ] Export logic for Top 50 CSV with trace persistence.

## Phase 4: Verification
- [ ] Verify heatmap visualization data structure.
- [ ] Ensure `logs/audit.jsonl` contains SHA-256 state hashes for cluster decisions.
- [ ] Test with `ACME-EU-90001` (Golden Path).
