# POC 2 — Account Planning Agent Mesh

## Mission
To automate the creation of high-value account briefs and strategic call plans for IQ-EQ sales leadership, leveraging the hardened LangGraph foundation.

## Technical Standards
- **Orchestration**: LangGraph StateGraph (Shared State: `PlanningState`).
- **Agents**: 
  - `ag-brief`: Generates 1-page contextual account snapshots.
  - `ag-plan`: Generates tactical call plans with discovery questions.
- **Resilience**:
  - `LLM_SEMAPHORE` (Rate limiting enforced).
  - `@retry` with exponential backoff on all nodes.
  - SHA-256 state auditing for compliance.

## End-to-End Flow
1. **Targeting Output** (Input State)
2. **Brief Agent**: Enrichment via external signals + internal data.
3. **Call Plan Agent**: Tactics definition and Discovery Questions.
4. **Validation Agent**: Cross-check against ICP (Ideal Customer Profile).
5. **Formatting Agent**: Final export to branded PDF/JSON.
