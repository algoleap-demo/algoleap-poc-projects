/* ─── Override Modal Component ───────────────────────────────────────────── */

const { useState, useEffect } = React;

window.OverrideModal = function OverrideModal({ account, onClose, onSaved }) {
    const [bucket, setBucket] = useState(account.priority_bucket || 'B');
    const [rationale, setRationale] = useState(account.rationale_text || '');
    const [category, setCategory] = useState('');
    const [notes, setNotes] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const bucketChanged = bucket !== account.priority_bucket;
    const rationaleChanged = rationale !== (account.rationale_text || '');
    const hasChanges = bucketChanged || rationaleChanged;
    const needsCategory = hasChanges;

    async function handleSave() {
        if (needsCategory && !category) {
            setError('You must select a failure category when overriding the AI output.');
            return;
        }
        setSaving(true);
        setError('');

        try {
            const overrides = [];

            if (bucketChanged) {
                overrides.push({
                    account_id: account.account_id,
                    field_changed: 'priority_bucket',
                    old_value: account.priority_bucket,
                    new_value: bucket,
                    failure_category: category,
                    notes: notes || undefined,
                });
            }

            if (rationaleChanged) {
                overrides.push({
                    account_id: account.account_id,
                    field_changed: 'rationale_text',
                    old_value: account.rationale_text || '',
                    new_value: rationale,
                    failure_category: category,
                    notes: notes || undefined,
                });
            }

            for (const ov of overrides) {
                await window.apiCreateOverride(ov);
            }

            onSaved && onSaved({
                ...account,
                priority_bucket: bucket,
                rationale_text: rationale,
            });
        } catch (e) {
            setError(e.message);
        } finally {
            setSaving(false);
        }
    }

    // Close on Escape
    useEffect(() => {
        function onKey(e) { if (e.key === 'Escape') onClose(); }
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    return (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div className="modal" role="dialog" aria-modal="true">
                <div className="modal-title">Override AI Prioritisation</div>
                <div className="modal-subtitle">
                    {account.account_id} — {account.name || account.account_id}
                </div>

                {/* AI suggestion (read-only) */}
                <div className="modal-ai-suggestion">
                    <div className="ai-label">🤖 AI Suggestion</div>
                    <div className="ai-value" style={{ marginBottom: 8 }}>
                        <strong>Priority:</strong>{' '}
                        <span className={`badge badge-${(account.priority_bucket || '').toLowerCase()}`}>
                            {account.priority_bucket}
                        </span>
                    </div>
                    <div className="ai-value">
                        <strong>Rationale:</strong> {account.rationale_text || '—'}
                    </div>
                </div>

                {/* Editable fields */}
                <div className="form-group">
                    <label htmlFor="override-bucket">Priority Bucket</label>
                    <select
                        id="override-bucket"
                        className="form-control"
                        value={bucket}
                        onChange={e => setBucket(e.target.value)}
                    >
                        <option value="A">A — High Priority</option>
                        <option value="B">B — Medium Priority</option>
                        <option value="C">C — Lower Priority</option>
                    </select>
                </div>

                <div className="form-group">
                    <label htmlFor="override-rationale">Rationale Text</label>
                    <textarea
                        id="override-rationale"
                        className="form-control"
                        value={rationale}
                        onChange={e => setRationale(e.target.value)}
                        maxLength={400}
                        rows={3}
                        placeholder="Enter your rationale (max 400 chars)"
                    />
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>
                        {rationale.length}/400
                    </div>
                </div>

                {/* Failure categorisation — required when override differs */}
                {needsCategory && (
                    <>
                        <div className="modal-divider" />
                        <div className="required-notice">
                            ⚠️ ISO 42001 requires categorising why the AI output was overridden.
                        </div>

                        <div className="form-group">
                            <label htmlFor="override-category">Failure Category *</label>
                            <select
                                id="override-category"
                                className="form-control"
                                value={category}
                                onChange={e => { setCategory(e.target.value); setError(''); }}
                            >
                                <option value="">— Select category —</option>
                                <option value="Policy Misalignment">Policy Misalignment</option>
                                <option value="Hallucination">Hallucination</option>
                                <option value="Data Latency">Data Latency</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="override-notes">Notes (optional)</label>
                            <textarea
                                id="override-notes"
                                className="form-control"
                                value={notes}
                                onChange={e => setNotes(e.target.value)}
                                rows={2}
                                placeholder="Additional context for the audit trail"
                            />
                        </div>
                    </>
                )}

                {error && (
                    <div style={{ color: 'var(--bucket-c)', fontSize: 13, marginTop: 8 }}>
                        {error}
                    </div>
                )}

                <div className="modal-actions">
                    <button className="btn btn-secondary" onClick={onClose} disabled={saving}>
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={saving || !hasChanges}
                    >
                        {saving ? 'Saving…' : 'Save Override'}
                    </button>
                </div>
            </div>
        </div>
    );
};
