# Antigravity Mission Standards: IQ-EQ Agent Mesh

This document is the **Authoritative Source of Truth** and governance manifest for the IQ-EQ Agent Mesh project. All AI agents (Antigravity) and development workflows must strictly adhere to these standards.

## 1. Architectural Architecture: The Linear Mesh Contract
The system is built as a **Linear Multi-Agent Mesh (6+ Agents)**.
- **Contract**: Orchestrator → Data → [Intel Layer] → Validation → Formatting.
- **Circuit Breaker**: No agent can be skipped. Sequential execution is mandatory.
- **Signal-to-Action**: Deterministic resolution tables are prohibited. Every Recommendation (NBA) must be dynamically synthesized from real-time customer signals via LLM reasoning.

## 2. High-Fidelity UI/UX Standards
- **Typography**: `Outfit` for Headers (700/800), `Inter` for Body text.
- **Aesthetics**: Vibrant colors, slate/dark-mode nuances, and premium rounded (12px-20px) radius borders.
- **Transparency**: Mandatory **Sequential Log Queueing**.
- **Micro-animations**: Log typing speed must be **15ms per character** to ensure a "Thinking" feel.
- **Layout**: Balanced 50/50 split between Mesh SVG and Data Pane.

## 3. Tech Stack & Integration
- **Framework**: FastAPI (Async) + Vanilla JS/CSS.
- **Reasoning Layer**: LangChain / LangGraph with OpenRouter (OpenAI-compatible) endpoint.
- **Data Governance**: 100% Synthetic data only.
- **Directory Structure**:
    - `data/raw/`: Initial synthetic generation.
    - `data/processed/`: Calibration and model-ready artifacts.
    - `.agent/skills/`: Reusable agent capabilities.

## 4. Coding & Governance
- **Naming**: `snake_case` (Python), `PascalCase` (UI Components).
- **Audit**: All agent transitions must be logged with Input/Output hashes for ISO 42001 compliance.
- **Environment**: All keys strictly in `.env`. No hardcoding.
