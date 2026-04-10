---
name: Algoleap Premium UI
description: Standards and base components for high-fidelity Algoleap Agentic POC dashboards.
---

# Algoleap Premium UI Skill (v2)

This skill provides the CSS and HTML patterns required to build "Algoleap Premium" dashboards—high-fidelity, glassmorphic interfaces designed for corporate Agentic POCs.

## Design Principles
1. **Agentic Transparency**: Use a visual "Agent Mesh" (SVG) with a **Horizontal Master Control** header to show real-time processing state.
2. **Glassmorphism**: Subtle blurs and borders to create a premium, layered feel.
3. **Typography (High Readability)**: 
   - **Headers**: `Outfit` (Bold, clean brand feel).
   - **Body**: `Inter` (Optimized for data legibility).
   - **Logs**: `Inter` (Large size, balanced line-height).
   - **Monospace**: `JetBrains Mono` (For Agent IDs and raw metrics).
4. **Color Palette**:
   - Primary Green: `#3C8943`
   - Orchestration Blue: `#1D4ED8`
   - Background Light: `#F9FAFB`

## UI Layout Standards
### 1. 50/50 Balanced Split
The dashboard is structured into a header, a horizontal view-selector, and a 2-column main area with a **1:1 (50/50) split**:
- **Left Column**: Architectural Mesh Canvas (`.canvas-container`).
- **Right Column**: Side Data Pane (`.data-pane`) for Logs and Results.
- This ensures that complex mesh visuals and dense data results are given equal visual priority.

### 2. Sequential Log Engine
To prevent "information overwhelm," logs must be rendered sequentially:
- **Promise-Based Queue**: Push incoming SSE events to a `msgQueue`.
- **Typwriter Persistence**: Each message card is created and typed out fully (15ms/char) before the next message in the queue is processed.
- **Synchronization**: SVG state transitions (Yellow/Green) must wait for the corresponding typewriter animation to resolve.

## Components

### 1. Response Card (Action Integrated)
Used to display final agent recommendations with integrated **Next Best Actions**.
```html
<div class="response-card">
    <div class="card-hdr">
        <div class="acc-id">Account Name</div>
        <div class="bucket-badge bucket-A">Bucket A</div>
    </div>
    <div class="rationale-box">
        <div class="rationale-text">LLM synthesized rationale.</div>
    </div>
    <div class="score-row">
        <div class="score-lbl">Score: 96.9%</div>
        <div class="nba-link">Next Best Action <span>&rarr;</span></div>
    </div>
    <div class="nba-panel">
        <!-- Collapsible panel containing bespoke LLM strategy -->
    </div>
</div>
```

### 2. SVG Mesh Architecture
- **Master Header**: A horizontal `<g id="ag-orch">` at the top of the SVG.
- **Initiate Flow**: A primary green arrow (`#arr-on`) pointing down to the Data Layer.
- **Return Loop**: A dashed return path from the final Formatting agent back to the Master Header to signify lifecycle completion.

## Usage
1. Use `Outfit` and `Inter` from Google Fonts.
2. Implement the `msgQueue` and `isProcessing` lock in the frontend JS to handle concurrent SSE bursts.
3. Ensure the `updStatus()` SVG logic triggers *after* the typewriter `resolve()` for completion states.
