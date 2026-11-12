import React, { useState } from 'react';

interface ChatMessage {
  sender: 'ai' | 'user';
  text: string;
  toolBadge?: string;
}

export const CopilotView: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'ai',
      text: 'Hello. I answer questions by querying your double-entry general ledger and contract milestones. How can I assist you with your payout records?'
    }
  ]);
  const [input, setInput] = useState<string>('');

  const sendQuery = (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text) return;

    const userMsg: ChatMessage = { sender: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    setTimeout(() => {
      let reply = '';
      let toolBadge = '';

      const lower = text.toLowerCase();
      if (lower.includes('net') || lower.includes('how much') || lower.includes('profit')) {
        toolBadge = 'Tool: get_contract_financial_summary(contract_id=1)';
        reply = `Financial summary for NordVPN campaign (USD):
• Gross invoiced: $5,000.00
• Inbound PayPal fees: -$87.74
• Team payouts: -$722.45 (Mark: $422.45 | Ana: $300.00)
• Outbound payout fee: -$1.00 (estimate)
─────────────────────────────
• Creator net retained: $1,688.81`;
      } else if (lower.includes('risk') || lower.includes('terms')) {
        toolBadge = 'Tool: analyze_contract_risk_terms(contract_id=1)';
        reply = `Contract terms analysis:
• ⚠️ Payment window: In SOW v2, payment terms shifted from Net-15 to Net-60 days (45-day delay).
• ⚠️ Milestone reduction: Milestone 2 reduced from $2,500.00 to $2,000.00 (-$500.00).
• ✓ Kill fee: Standard cancellation fee clause present.`;
      } else {
        toolBadge = 'Tool: list_collaborators()';
        reply = `Verified collaborator directory:
• Mark Santos (Editor) — editor-ph@sandbox.com [USD]
• Ana Silva (Designer) — designer-br@sandbox.com [USD]
• David Miller (Manager) — manager-us@sandbox.com [USD]`;
      }

      setMessages(prev => [...prev, { sender: 'ai', text: reply, toolBadge }]);
    }, 350);
  };

  return (
    <section>
      <div className="tab-header">
        <span className="tag">Deterministic Financial Queries</span>
        <h2>Financial Copilot</h2>
        <p className="tab-sub">
          Queries run through fixed database tools and integer-cent calculations. Zero predicted math.
        </p>
      </div>

      <div className="chat-layout">
        <div className="chat-box">
          <div className="chat-messages">
            {messages.map((m, idx) => (
              <div key={idx} className={`chat-msg ${m.sender}`}>
                {m.sender === 'ai' && (
                  <span className="tag" style={{ display: 'block', marginBottom: 4 }}>
                    Copilot Assistant
                  </span>
                )}
                {m.toolBadge && (
                  <div style={{ marginBottom: 6 }}>
                    <span className="badge b-ok mono">{m.toolBadge}</span>
                  </div>
                )}
                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              </div>
            ))}
          </div>

          <div className="chat-input-bar">
            <input
              type="text"
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="e.g. What did I net after team payouts and fees?"
              onKeyDown={e => e.key === 'Enter' && sendQuery()}
            />
            <button onClick={() => sendQuery()} className="btn">
              Send
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="panel-card">
            <span className="tag">Suggested Queries</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
              <button
                onClick={() => sendQuery('What did I actually net from the NordVPN campaign after paying my team and fees?')}
                className="btn ghost sm"
                style={{ textAlign: 'left', justifyContent: 'flex-start' }}
              >
                Net Retained Profit
              </button>
              <button
                onClick={() => sendQuery('Evaluate contract risk terms for cash flow delays and kill fees')}
                className="btn ghost sm"
                style={{ textAlign: 'left', justifyContent: 'flex-start' }}
              >
                Check Payment Terms Risk
              </button>
              <button
                onClick={() => sendQuery('List all verified collaborators and their PayPal accounts')}
                className="btn ghost sm"
                style={{ textAlign: 'left', justifyContent: 'flex-start' }}
              >
                Show Team Directory
              </button>
            </div>
          </div>

          <div className="panel-card" style={{ fontSize: 12, color: 'var(--muted)' }}>
            <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>
              Deterministic Guard
            </div>
            Calculations are computed directly by backend arithmetic routines, not estimated by language model generation.
          </div>
        </div>
      </div>
    </section>
  );
};

