/* ─── API Client ─────────────────────────────────────────────────────────── */

const API_BASE = window.location.port === '5500' || window.location.port === '5501'
    ? 'http://localhost:8000'    // Live-server dev
    : '';                        // Same-origin when served by FastAPI

async function apiFetch(path, options = {}) {
    const resp = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(`API ${resp.status}: ${detail}`);
    }
    return resp.json();
}

// Phase 3 — scoring
window.apiScoreAccounts = function (filters) {
    return apiFetch('/score_accounts', {
        method: 'POST',
        body: JSON.stringify(filters),
    });
};

// Phase 4 — LLM prioritisation
window.apiPrioritizeAccounts = function (filters) {
    return apiFetch('/prioritize_accounts', {
        method: 'POST',
        body: JSON.stringify(filters),
    });
};

// Phase 5 — overrides
window.apiCreateOverride = function (payload) {
    return apiFetch('/overrides', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
};

window.apiListOverrides = function (params = {}) {
    const qs = new URLSearchParams(params).toString();
    return apiFetch(`/overrides${qs ? '?' + qs : ''}`);
};

window.apiOverridesSummary = function () {
    return apiFetch('/overrides/summary');
};

window.apiGetCountries = function () {
    return apiFetch('/metadata/countries');
};

window.apiCopilotAsk = function (message) {
    return apiFetch('/copilot/ask', {
        method: 'POST',
        body: JSON.stringify({ message }),
    });
};

window.apiHealth = function () {
    return apiFetch('/health');
};
