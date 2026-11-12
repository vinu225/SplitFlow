import React, { useState } from 'react';

interface ContractsViewProps {
  sowVersion: number;
  onInvoiceCreated: () => void;
}

export const ContractsView: React.FC<ContractsViewProps> = ({
  sowVersion,
  onInvoiceCreated
}) => {
  const [activeHighlight, setActiveHighlight] = useState<number>(1);
  const [amendmentAccepted, setAmendmentAccepted] = useState<boolean>(false);
  const [invoiceState, setInvoiceState] = useState<'ready' | 'dispatching' | 'sent'>('ready');

  const handleCreateInvoice = () => {
    setInvoiceState('dispatching');
    setTimeout(() => {
      setInvoiceState('sent');
      onInvoiceCreated();
    }, 700);
  };

  return (
    <section>
      <div className="tab-header">
        <span className="tag">Contract Ingestion & Verification</span>
        <h2>Contracts</h2>
        <p className="tab-sub">
          Each extracted amount is checked against verbatim clauses. Click any clause to verify the source text.
        </p>
      </div>

      {sowVersion === 2 && !amendmentAccepted && (
        <div className="alert-banner">
          <div>
            <h4>Contract amendment detected</h4>
            <p>
              Payment window changed from Net-15 to Net-60. Milestone 2 reduced from $2,500.00 to $2,000.00 (-$500.00). Payout staging is locked.
            </p>
          </div>
          <button onClick={() => setAmendmentAccepted(true)} className="btn">
            Accept & Re-approve
          </button>
        </div>
      )}

      <div className="dash-grid">
        {/* Left: Source Document Preview */}
        <div className="panel-card">
          <div className="row">
            <span className="tag">Source Document</span>
            <span className="badge mono">
              {sowVersion === 1 ? 'SHA: a7f8c9d0...' : 'SHA: b3e4f5a1...'}
            </span>
          </div>
          <div style={{ margin: '10px 0 6px', fontWeight: 700 }}>
            {sowVersion === 1
              ? 'NordVPN_Sponsorship_Agreement_v1.pdf'
              : 'NordVPN_Sponsorship_Agreement_v2.pdf (Amended)'}
          </div>

          <div className="clause-box">
            <div style={{ fontWeight: 700, marginBottom: 8 }}>
              STATEMENT OF WORK #2026-NORD-01
            </div>
            <div style={{ color: 'var(--muted)', marginBottom: 12 }}>
              Sponsor: NordVPN Global · Creator: Apex Media Studios
            </div>

            <div
              className={`clause-item ${activeHighlight === 1 ? 'highlight-active' : ''}`}
              onClick={() => setActiveHighlight(1)}
            >
              • <b>Milestone 1: $2,500.00 USD</b> (50% due upon mutual signing). Deliverable: Script draft & storyboard concept.
            </div>

            <div
              className={`clause-item ${activeHighlight === 2 ? 'highlight-active' : ''}`}
              onClick={() => setActiveHighlight(2)}
            >
              • <b>Milestone 2: {sowVersion === 1 ? '$2,500.00 USD' : '$2,000.00 USD'}</b> (50% within {sowVersion === 1 ? '14' : '60'} days of publication). Deliverable: Final video live publication.
            </div>

            <div className="clause-item" style={{ color: 'var(--muted)' }}>
              • Settlement terms: All invoices payable via PayPal {sowVersion === 1 ? 'Net-15' : 'Net-60'} days. Standard kill fee applies.
            </div>
          </div>

          <div className="row" style={{ marginTop: 12, borderBottom: 0 }}>
            <span style={{ color: 'var(--muted)', fontSize: 12 }}>Quote status</span>
            <span className="badge b-ok">Source quote verified</span>
          </div>
        </div>

        {/* Right: Split Schedule */}
        <div className="panel-card">
          <div className="row">
            <span className="tag">Split Schedule</span>
            <span className="badge b-ok">Totals match</span>
          </div>

          <div style={{ margin: '12px 0 16px' }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>Milestone 1: Deposit</div>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>
              Gross target: <span className="mono" style={{ color: 'var(--text)', fontWeight: 700 }}>$2,500.00 USD</span>
            </div>
          </div>

          <div style={{ background: 'var(--panel)', padding: 12, borderRadius: 2, marginBottom: 16 }}>
            <div className="row">
              <span>Ana Silva (Designer)</span>
              <b className="mono">$300.00 flat priority</b>
            </div>
            <div className="row">
              <span>Mark Santos (Editor)</span>
              <b className="mono">20.00% net remainder</b>
            </div>
            <div className="row">
              <span>Apex Media (Creator)</span>
              <b className="mono">Remainder pool retention</b>
            </div>
          </div>

          <div className="row">
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>
              {invoiceState === 'ready' && 'Invoice state: Ready to dispatch'}
              {invoiceState === 'dispatching' && 'Invoice state: Dispatching via PayPal...'}
              {invoiceState === 'sent' && (
                <span>
                  Invoice: <span className="mono">INV2-NORD-991A</span>
                </span>
              )}
            </span>
            <button
              onClick={handleCreateInvoice}
              disabled={invoiceState !== 'ready'}
              className={`btn ${invoiceState === 'sent' ? 'ghost' : ''}`}
            >
              {invoiceState === 'ready' && 'Generate PayPal Invoice'}
              {invoiceState === 'dispatching' && 'Dispatching...'}
              {invoiceState === 'sent' && 'Invoice Sent'}
            </button>
          </div>

          <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
            <div className="row">
              <span>Milestone 2 (Scheduled)</span>
              <b className="mono">
                {sowVersion === 1 ? '$2,500.00 USD' : '$2,000.00 USD (-$500.00)'}
              </b>
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 4 }}>
              Pending publication telemetry & contract term confirmation.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

