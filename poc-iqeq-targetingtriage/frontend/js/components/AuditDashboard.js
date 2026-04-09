/* ─── Audit Dashboard Component ──────────────────────────────────────────── */

const { useState, useEffect, useCallback } = React;

const CATEGORY_COLORS = {
    'Policy Misalignment': { css: 'var(--cat-policy)',       hex: '#8b5cf6', className: 'policy' },
    'Hallucination':       { css: 'var(--cat-hallucination)', hex: '#f43f5e', className: 'hallucination' },
    'Data Latency':        { css: 'var(--cat-latency)',       hex: '#06b6d4', className: 'latency' },
};

const BADGE_MAP = {
    'Policy Misalignment': 'badge-policy',
    'Hallucination':       'badge-hallucination',
    'Data Latency':        'badge-latency',
};

function DonutChart({ data, total }) {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    const entries = Object.entries(data);

    let accumulated = 0;
    const segments = entries.map(([cat, count]) => {
        const pct = total > 0 ? count / total : 0;
        const dashArray = `${pct * circumference} ${circumference}`;
        const offset = accumulated * circumference;
        accumulated += pct;
        return { cat, count, dashArray, offset, color: (CATEGORY_COLORS[cat] || {}).hex || '#666' };
    });

    return (
        <div className="donut-container">
            <div className="donut-ring">
                <svg viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r={radius} stroke="var(--bg-input)" />
                    {segments.map((s, i) => (
                        <circle
                            key={i}
                            cx="60" cy="60" r={radius}
                            stroke={s.color}
                            strokeDasharray={s.dashArray}
                            strokeDashoffset={-s.offset}
                        />
                    ))}
                </svg>
                <div className="donut-center">
                    <span className="donut-total">{total}</span>
                    <span className="donut-label">Total</span>
                </div>
            </div>
            <div className="donut-legend">
                {entries.map(([cat, count]) => (
                    <div className="legend-item" key={cat}>
                        <span className="legend-dot" style={{ background: (CATEGORY_COLORS[cat] || {}).hex || '#666' }} />
                        <span>{cat}</span>
                        <span className="legend-count">{count}</span>
                    </div>
                ))}
                {entries.length === 0 && (
                    <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>No overrides yet</span>
                )}
            </div>
        </div>
    );
}

function BarChart({ data, total }) {
    const entries = Object.entries(data);
    const maxVal = Math.max(...entries.map(([, v]) => v), 1);

    return (
        <div className="bar-chart">
            {entries.map(([cat, count]) => (
                <div className="bar-item" key={cat}>
                    <span className="bar-label">{cat}</span>
                    <div className="bar-track">
                        <div
                            className={`bar-fill ${(CATEGORY_COLORS[cat] || {}).className || ''}`}
                            style={{ width: `${(count / maxVal) * 100}%` }}
                        >
                            {count}
                        </div>
                    </div>
                </div>
            ))}
            {entries.length === 0 && (
                <span style={{ color: 'var(--text-muted)', fontSize: 13, padding: 20 }}>No data</span>
            )}
        </div>
    );
}

window.AuditDashboard = function AuditDashboard({ refreshTrigger }) {
    const [summary, setSummary] = useState(null);
    const [overrides, setOverrides] = useState([]);
    const [filterCat, setFilterCat] = useState('');
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [sumData, ovData] = await Promise.all([
                window.apiOverridesSummary(),
                window.apiListOverrides(filterCat ? { failure_category: filterCat } : {}),
            ]);
            setSummary(sumData);
            setOverrides(ovData);
        } catch (e) {
            console.error('Audit fetch error:', e);
        } finally {
            setLoading(false);
        }
    }, [filterCat, refreshTrigger]);

    useEffect(() => { fetchData(); }, [fetchData]);

    if (loading && !summary) return <div className="loading">Loading audit data…</div>;

    const total = summary ? summary.total : 0;
    const byCat = summary ? summary.by_category : {};
    const byField = summary ? summary.by_field : {};

    return (
        <div>
            <div className="page-header">
                <h2>Audit Dashboard</h2>
                <p>ISO 42001 governance overview — track all human overrides with failure categorisation.</p>
            </div>

            {/* Stat cards */}
            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--accent)' }}>{total}</div>
                    <div className="stat-label">Total Overrides</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--cat-policy)' }}>
                        {byCat['Policy Misalignment'] || 0}
                    </div>
                    <div className="stat-label">Policy Misalignment</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--cat-hallucination)' }}>
                        {byCat['Hallucination'] || 0}
                    </div>
                    <div className="stat-label">Hallucination</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--cat-latency)' }}>
                        {byCat['Data Latency'] || 0}
                    </div>
                    <div className="stat-label">Data Latency</div>
                </div>
            </div>

            {/* Charts */}
            <div className="chart-grid">
                <div className="chart-card">
                    <h3>Override Distribution</h3>
                    <DonutChart data={byCat} total={total} />
                </div>
                <div className="chart-card">
                    <h3>By Failure Category</h3>
                    <BarChart data={byCat} total={total} />
                </div>
            </div>

            {/* Override log */}
            <div className="card">
                <div className="card-header">
                    <h3>Override Log</h3>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                            className="form-control"
                            style={{ width: 200, marginBottom: 0 }}
                            value={filterCat}
                            onChange={e => setFilterCat(e.target.value)}
                        >
                            <option value="">All Categories</option>
                            <option value="Policy Misalignment">Policy Misalignment</option>
                            <option value="Hallucination">Hallucination</option>
                            <option value="Data Latency">Data Latency</option>
                        </select>
                        <button className="btn btn-secondary btn-sm" onClick={fetchData}>↻ Refresh</button>
                    </div>
                </div>

                {overrides.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">📋</div>
                        <p>No override records found. Overrides will appear here once you modify AI prioritisations.</p>
                    </div>
                ) : (
                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>User</th>
                                    <th>Account</th>
                                    <th>Field</th>
                                    <th>Old → New</th>
                                    <th>Category</th>
                                    <th>Notes</th>
                                </tr>
                            </thead>
                            <tbody>
                                {overrides.map(o => (
                                    <tr key={o.id}>
                                        <td style={{ fontSize: 12 }}>
                                            {new Date(o.timestamp).toLocaleString()}
                                        </td>
                                        <td>{o.user}</td>
                                        <td>{o.account_id}</td>
                                        <td>
                                            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                                {o.field_changed}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: 'var(--bucket-c)', fontWeight: 500 }}>{o.old_value}</span>
                                            {' → '}
                                            <span style={{ color: 'var(--bucket-a)', fontWeight: 500 }}>{o.new_value}</span>
                                        </td>
                                        <td>
                                            <span className={`badge-category ${BADGE_MAP[o.failure_category] || ''}`}>
                                                {o.failure_category}
                                            </span>
                                        </td>
                                        <td style={{ whiteSpace: 'normal', maxWidth: 200, fontSize: 12 }}>
                                            {o.notes || '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};
