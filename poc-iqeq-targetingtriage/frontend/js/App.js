/* ─── App Root ───────────────────────────────────────────────────────────── */

const { useState, useCallback } = React;

function App() {
    const [view, setView] = useState('audit');
    const [auditRefresh, setAuditRefresh] = useState(0);

    const triggerAuditRefresh = useCallback(() => {
        setAuditRefresh(prev => prev + 1);
    }, []);

    return (
        <div className="app-layout-horizontal">
            {/* Top Navigation */}
            <header className="top-nav-bar">
                <div className="page-container align-nav">
                    <img src="/ui/assets/Algoleap_logo.png" alt="Algoleap" className="brand-logo-img" />
                    <nav className="top-nav-links">
                        <button
                            className={view === 'audit' ? 'active' : ''}
                            onClick={() => setView('audit')}
                        >
                            📊 Audit Dashboard
                        </button>
                        <button
                            className={view === 'prioritise' ? 'active' : ''}
                            onClick={() => setView('prioritise')}
                        >
                            🎯 Prioritisation
                        </button>
                        <button
                            className={view === 'copilot' ? 'active' : ''}
                            onClick={() => setView('copilot')}
                        >
                            ✨ Data Copilot
                        </button>
                    </nav>
                </div>
            </header>

            {/* Sub-Header Title Banner */}
            <div className="workbench-title-banner">
                <div className="page-container">
                    <h1>IQ-EQ Workbench</h1>
                    <p>ISO 42001 Governance</p>
                </div>
            </div>

            {/* Main content */}
            <main className="main-content-horizontal">
                <div className="page-container">
                    <div style={{ display: view === 'prioritise' ? 'block' : 'none' }}>
                        <window.PrioritisationView onOverrideCountChange={triggerAuditRefresh} />
                    </div>
                    <div style={{ display: view === 'audit' ? 'block' : 'none' }}>
                        <window.AuditDashboard refreshTrigger={auditRefresh} />
                    </div>
                    <div style={{ display: view === 'copilot' ? 'block' : 'none' }}>
                        <window.CopilotView />
                    </div>
                </div>
            </main>

            {/* App Footer */}
            <footer className="app-footer">
                IQ-EQ Targeting & Triage Agent — POC v1.0 — Synthetic Data Only
            </footer>
        </div>
    );
}

// Mount
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
