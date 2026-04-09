/* ─── Data Copilot View ──────────────────────────────────────────────────── */

const { useState, useRef, useEffect } = React;

window.CopilotView = function CopilotView() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am the IQ-EQ Data Copilot. I have access to your most recent scored accounts and audit overrides. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    async function handleSend(e) {
        e?.preventDefault();
        const msg = input.trim();
        if (!msg || loading) return;

        // Add user message
        const newMessages = [...messages, { role: 'user', content: msg }];
        setMessages(newMessages);
        setInput('');
        setLoading(true);

        try {
            // Send just the latest message to the backend (which injects system data)
            const response = await window.apiCopilotAsk(msg);
            setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
        } catch (error) {
            console.error("Copilot Error:", error);
            const errorMsg = error.message.includes('TOKEN EXHAUSTION ERROR') 
                ? "⚠️ **Token Expiration Alert:** The data context or the length of the generated response exceeded the AI's maximum allowed memory (tokens). Please try asking a more specific question!"
                : `❌ **System Error:** ${error.message}`;
            
            setMessages(prev => [...prev, { role: 'assistant', content: errorMsg, isError: true }]);
        } finally {
            setLoading(false);
        }
    }

    // Markdown parser (very basic implementation for bold and line breaks)
    function formatMessage(text) {
        if (!text) return null;
        return text.split('\n').map((line, i) => {
            // Bold
            let formattedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Basic bullet points
            if (formattedLine.trim().startsWith('* ')) {
                formattedLine = `• ${formattedLine.substring(2)}`;
            } else if (formattedLine.trim().startsWith('- ')) {
                formattedLine = `• ${formattedLine.substring(2)}`;
            }
            return <div key={i} dangerouslySetInnerHTML={{ __html: formattedLine || '<br/>' }} style={{ minHeight: '1em' }} />;
        });
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="page-header" style={{ marginBottom: 16 }}>
                <h2>Data Copilot</h2>
                <p>Ask natural questions about your accounts, priority buckets, and audit trails powered by Gemini.</p>
            </div>

            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
                {/* Chat History */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {messages.map((msg, idx) => (
                        <div key={idx} style={{ 
                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '80%',
                            background: msg.role === 'user' ? 'var(--accent)' : (msg.isError ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-secondary)'),
                            color: msg.role === 'user' ? '#fff' : (msg.isError ? 'var(--bucket-c)' : 'var(--text-primary)'),
                            border: msg.isError ? '1px solid var(--bucket-c)' : `1px solid ${msg.role === 'user' ? 'var(--accent)' : 'var(--border)'}`,
                            padding: '16px 20px',
                            borderRadius: '16px',
                            borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
                            borderTopLeftRadius: msg.role === 'assistant' ? '4px' : '16px',
                            fontSize: '14px',
                            lineHeight: '1.6'
                        }}>
                            {formatMessage(msg.content)}
                        </div>
                    ))}
                    {loading && (
                        <div style={{ 
                            alignSelf: 'flex-start',
                            background: 'var(--bg-secondary)',
                            border: '1px solid var(--border)',
                            padding: '16px 20px',
                            borderRadius: '16px',
                            borderTopLeftRadius: '4px',
                            fontSize: '13px',
                            color: 'var(--text-muted)'
                        }}>
                            Analyzing Live Database...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Chat Input */}
                <form onSubmit={handleSend} style={{ padding: '20px', borderTop: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <input
                            type="text"
                            className="form-control"
                            style={{ flex: 1, padding: '14px 20px', fontSize: '14px', borderRadius: '24px' }}
                            placeholder="e.g., Which accounts in NL have an upcoming launch?"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={loading}
                        />
                        <button type="submit" className="btn btn-primary" style={{ borderRadius: '24px', padding: '0 24px' }} disabled={loading || !input.trim()}>
                            {loading ? '...' : 'Send'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
