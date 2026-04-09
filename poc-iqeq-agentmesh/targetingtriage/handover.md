# Handover Document: IQ-EQ Agent Mesh (POC1)

## 🎯 POC1 Summary
The Targeting & Triage POC successfully demonstrates a multi-agent system that combines statistical machine learning (XGBoost) with semantic reasoning (LLM). 

### Key Achievements
- **Model Accuracy**: AUC 1.00 on synthetic datasets.
- **100% Signal-to-Action**: Replaced deterministic NBA lookups with LLM-synthesized context-aware strategy generation.
- **Dynamic Confidence**: Implemented probability-based confidence scaling ($abs(prob - 0.5) / 0.5$) for honest AI assessment.
- **ISO 42001 Compliance**: Hand-engineered conflict detection and cryptographic audit logging.

---

## 🛠️ Technical Baseline
- **Language**: Python 3.11+
- **ML Framework**: XGBoost (Calibrated via Isotonic Regression)
- **API**: FastAPI with SSE for real-time progress.
- **Frontend**: Vanilla JS/CSS (Algoleap deep-dark theme).

### Source of Truth (STOT)
Developers must respect `app/features.py` as the **Single Source of Truth** for all feature aggregation. Any changes to the feature vector here must be followed by a model retrain via `scripts/train_xgb.py`.

---

## 🚀 Roadmap for POC2 (Account Planning)
The next phase involve building the "Brief Agent" and "Call Plan Agent".

### Recommendations:
1. **Brief Agent**: Should extend `app/agents/` and ingest account context to generate markdown-formatted summaries.
2. **Total Autonomy**: New NBAs are generated dynamically by the LLM based on user segment and country signals. The rule-based mapping in `formatting_agent.py` has been deprecated.
3. **Audit Continuity**: Ensure the `log_audit()` hashing pattern is maintained for new agents to keep the cryptographic chain intact.

---

## ⚖️ Governance & Review
The `logs/governance_queue.jsonl` contains all accounts flagged for manual review. In POC2, these should be surfaced in the **Governance Workbench** (UI) to allow human analysts to override bucket assignments before the "Call Plan" is finalized.

---

## 🧹 Final Workspace State
- `tmp/`: Cleaned (scratch files removed).
- `models/`: Contains the production-ready `xgb_propensity_v1.pkl`.
- `data/`: Contains the hand-engineered conflict samples for regression testing.
