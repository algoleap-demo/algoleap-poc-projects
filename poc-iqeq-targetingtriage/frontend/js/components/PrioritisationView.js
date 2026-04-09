/* ─── Prioritisation View Component ──────────────────────────────────────── */

const { useState, useEffect, useCallback } = React;

window.PrioritisationView = function PrioritisationView({ onOverrideCountChange }) {
    const [countries, setCountries] = useState('');
    const [availableCountries, setAvailableCountries] = useState([]);
    const [statusFilter, setStatusFilter] = useState('');
    const [minPropensity, setMinPropensity] = useState('');
    const [limit, setLimit] = useState('30');
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [modalAccount, setModalAccount] = useState(null);
    const [toast, setToast] = useState('');

    useEffect(() => {
        window.apiGetCountries()
            .then(data => setAvailableCountries(data))
            .catch(err => console.error("Failed to load available countries:", err));
    }, []);

    const handlePrioritize = useCallback(async () => {
        setLoading(true);
        setError('');
        setResults(null);
        try {
            const filters = {};
            if (countries.trim()) {
                const reqCountries = countries.split(',').map(c => c.trim().toUpperCase()).filter(Boolean);
                if (availableCountries.length > 0) {
                    const invalid = reqCountries.filter(c => !availableCountries.includes(c));
                    if (invalid.length > 0) {
                        throw new Error(`Invalid countries entered: ${invalid.join(', ')}. Available are: ${availableCountries.join(', ')}`);
                    }
                }
                filters.countries = reqCountries;
            }
            if (statusFilter) filters.status_filter = statusFilter;
            if (minPropensity) filters.min_propensity = parseFloat(minPropensity);
            if (limit) filters.limit = parseInt(limit, 10);

            const data = await window.apiPrioritizeAccounts(filters);
            setResults(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [countries, statusFilter, minPropensity, limit]);

    function downloadCSV() {
        if (!results || !results.results) return;
        const rows = results.results;
        const headers = ['account_id', 'priority_bucket', 'rationale_text'];
        const csv = [
            headers.join(','),
            ...rows.map(r =>
                [r.account_id, r.priority_bucket, `"${(r.rationale_text || '').replace(/"/g, '""')}"`].join(',')
            ),
        ].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `prioritised_accounts_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function handleOverrideSaved(updatedAccount) {
        setModalAccount(null);
        // Update the results table in place
        if (results) {
            const updatedResults = results.results.map(r =>
                r.account_id === updatedAccount.account_id ? updatedAccount : r
            );
            setResults({ ...results, results: updatedResults });
        }
        setToast(`Override saved for ${updatedAccount.account_id}`);
        onOverrideCountChange && onOverrideCountChange();
        setTimeout(() => setToast(''), 3000);
    }

    return (
        <div>
            <div className="page-header">
                <h2>Account Prioritisation</h2>
                <p>Run LLM-powered prioritisation and review AI-assigned A/B/C buckets with rationale.</p>
            </div>

            {/* Filter bar */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="filter-bar">
                    <div className="form-group">
                        <label htmlFor="filter-countries">
                            Countries 
                            {availableCountries.length > 0 && (
                                <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'none', marginLeft: 8 }}>
                                    (Available: {availableCountries.join(', ')})
                                </span>
                            )}
                        </label>
                        <input
                            id="filter-countries"
                            className="form-control"
                            placeholder={availableCountries.length > 0 ? `e.g. ${availableCountries.slice(0,2).join(', ')}` : "e.g. NL, LU"}
                            value={countries}
                            onChange={e => setCountries(e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="filter-status">Status</label>
                        <select id="filter-status" className="form-control" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                            <option value="">All</option>
                            <option value="client">Client</option>
                            <option value="prospect">Prospect</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label htmlFor="filter-propensity">Min Propensity</label>
                        <input
                            id="filter-propensity"
                            className="form-control"
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            placeholder="0.0"
                            value={minPropensity}
                            onChange={e => setMinPropensity(e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="filter-limit">Limit</label>
                        <input
                            id="filter-limit"
                            className="form-control"
                            type="number"
                            min="1"
                            max="200"
                            value={limit}
                            onChange={e => setLimit(e.target.value)}
                        />
                    </div>
                    <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                        <button className="btn btn-primary" onClick={handlePrioritize} disabled={loading}>
                            {loading ? '⏳ Running…' : '🚀 Prioritise'}
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="card" style={{ borderColor: 'var(--bucket-c)', marginBottom: 24, color: 'var(--bucket-c)' }}>
                    <strong>Error:</strong> {error}
                </div>
            )}

            {loading && <div className="loading">Calling Gemini for prioritisation…</div>}

            {/* Results */}
            {results && !loading && (
                <div className="card">
                    <div className="card-header">
                        <h3>
                            {results.results.length} Account{results.results.length !== 1 ? 's' : ''} Prioritised
                            <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: 12, marginLeft: 10 }}>
                                via {results.llm_provider}/{results.llm_model} • {results.prompt_version}
                            </span>
                        </h3>
                        <button className="btn btn-secondary btn-sm btn-export" onClick={downloadCSV}>
                            📥 Export CSV
                        </button>
                    </div>

                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Account ID</th>
                                    <th>Bucket</th>
                                    <th>Rationale</th>
                                    <th style={{ textAlign: 'center' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {results.results.map(r => (
                                    <tr key={r.account_id}>
                                        <td>{r.account_id}</td>
                                        <td>
                                            <span className={`badge badge-${r.priority_bucket.toLowerCase()}`}>
                                                {r.priority_bucket}
                                            </span>
                                        </td>
                                        <td style={{ whiteSpace: 'normal', maxWidth: 500 }}>
                                            {r.rationale_text}
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <button className="btn-override" onClick={() => setModalAccount(r)}>
                                                ✏️ Override
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {!results && !loading && !error && (
                <div className="empty-state">
                    <div className="empty-icon">📊</div>
                    <p>Select filters above and click "Prioritise" to generate an AI-ranked account list.</p>
                </div>
            )}

            {/* Override modal */}
            {modalAccount && (
                <window.OverrideModal
                    account={modalAccount}
                    onClose={() => setModalAccount(null)}
                    onSaved={handleOverrideSaved}
                />
            )}

            {/* Toast notification */}
            {toast && <div className="toast">✅ {toast}</div>}
        </div>
    );
};
