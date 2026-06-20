# Aligning Propensity Calculation with Reference Image

The user's reference image specifies a three-layered propensity model with specific feature groupings and thematic weights. While most signals (Win Rate, Deal Size, Service Penetration, Launches, Conferences) are already implemented, `Revenue Concentration` is missing, and the thematic grouping should be explicitly reflected in the agent reasoning.

## User Review Required

> [!IMPORTANT]
> The image shows **Specific Weights** (60%, 80%, 100%) for feature groups. In our current XGBoost implementation, weights are **learned** from training data, not manually set. To adhere strictly to the visual requirement, I will:
> 1. Add the missing `Revenue Concentration` feature to the data and model pipeline.
> 2. Update the **Reasoning Agent** to group signals into these three thematic layers (Historical, Firmographic, Timing) in its rationale.

## Proposed Changes

### 1. Data Layer Alignment

#### [MODIFY] [data_gen.py](file:///c:/Projects/algoleap-poc-projects/poc-iqeq-agentmesh/app/data_gen.py)
- Update `generate_snowflake_metrics` to include a `revenue_concentration` column.

#### [RUN] Data Regeneration
- Execute `python scripts/generate_training_data.py`
- Execute `python scripts/generate_runtime_data.py`

### 2. Feature & Pipeline Alignment

#### [MODIFY] [features.py](file:///c:/Projects/algoleap-poc-projects/poc-iqeq-agentmesh/app/core/features.py)
- Update `compute_features` to include `revenue_concentration` in the feature vector.

#### [MODIFY] [constants.py](file:///c:/Projects/algoleap-poc-projects/poc-iqeq-agentmesh/app/core/constants.py)
- Update `FEATURE_ORDER` to include `revenue_concentration`.

### 3. Reasoning & Presentation Layer

#### [MODIFY] [reasoning_agent.py](file:///c:/Projects/algoleap-poc-projects/poc-iqeq-agentmesh/app/modules/targeting/reasoning_agent.py)
- Update the `REASONING_PROMPT` to instruct the LLM to structure its rationale based on:
    - **Historical Weight** (60%)
    - **Firmographics** (80%)
    - **Timing Signals** (100%)

## Verification Plan

### Automated Verification
- Run a test mission and verify `revenue_concentration` appearing in the processing logs.
- Verify LLM rationales align with the three-weight structure.

### Manual Verification
- Review the Pricing Dashboard results to ensure "Revenue Concentration" is cited in Priority A accounts.
