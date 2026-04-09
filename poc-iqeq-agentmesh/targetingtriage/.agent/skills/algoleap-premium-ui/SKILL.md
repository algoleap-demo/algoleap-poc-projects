---
name: Algoleap Premium UI
description: Standards and base components for high-fidelity Algoleap Agentic POC dashboards.
---

# Algoleap Premium UI Skill

This skill provides the CSS and HTML patterns required to build "Algoleap Premium" dashboards—high-fidelity, glassmorphic interfaces designed for corporate Agentic POCs.

## Design Principles
1. **Agentic Transparency**: Use a visual "Agent Mesh" (SVG) to show real-time processing state.
2. **Glassmorphism**: Subtle blurs and borders to create a premium, layered feel.
3. **Typography**: Use `Syne` for headers, `Inter/Roboto` for body, and `JetBrains Mono` for agent logs.
4. **Color Palette**:
   - Primary Green: `#3C8943`
   - Orchestration Blue: `#1D4ED8`
   - Background Light: `#F9FAFB`

## Components

### 1. 3-Pane Layout
The dashboard is structured into a header, a horizontal view-selector, and a 2-column main area (70/30 split):
- **Left Column**: Visualization Canvas (`.canvas-container`)
- **Right Column**: Side Panel (`.data-pane`) for Logs and Results.

### 2. Response Card
Used to display final agent recommendations.
```html
<div class="response-card">
    <div class="card-hdr">
        <div class="acc-id">Account Name (ID)</div>
        <div class="bucket-badge bucket-A">Bucket A</div>
    </div>
    <div class="rationale-box">
        <div class="rationale-text">Agent rationale text goes here.</div>
    </div>
    <div class="score-row">
        <div class="score-lbl">Score: 96.9%</div>
        <div class="nba-link">View Actions &rarr;</div>
    </div>
</div>
```

### 3. Trace Card (Logs)
Used for real-time SSE progress updates.
```html
<div class="trace-card">
    <div class="trace-hdr">
        <div class="trace-status active"></div>
        <div class="trace-agent">AGENT-NAME</div>
    </div>
    <div class="trace-desc">Processing message...</div>
</div>
```

### 4. Interactive SVG Mesh
Use the classes `ag-active` and `ag-completed` on SVG groups (`<g>`) to trigger status highlights and pulse animations.

## Usage
1. Reference `resources/algoleap-base.css` in your HTML.
2. Use `resources/template.html` as a boilerplate for new projects.
3. Ensure your backend returns the following schema for card compatibility:
```json
{
  "account_name": "string",
  "priority_bucket": "A|B|C",
  "ml_score": "float",
  "rationale_text": "string"
}
```
