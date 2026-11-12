import React, { useState } from 'react';

interface StagedPayoutsViewProps {
  onPayoutApproved: () => void;
}

export const StagedPayoutsView: React.FC<StagedPayoutsViewProps> = ({ onPayoutApproved }) => {
  const [payoutState, setPayoutState] = useState<'staged' | 'dispatching' | 'settled'>('staged');

  const handleSimulateWebhook = () => {
    alert(
      "Webhook INVOICING.INVOICE.PAID received!\n\n• Event: WH-8812\n• Capture Ref: CAP-2026-991A\n• Net received: $2,412.26 USD (Gross: $2,500.00 - Inbound fee: $87.74)\n• Staged payouts calculated."
    );
  };

  const handleApprovePayout = () => {
    setPayoutState('dispatching');
    setTimeout(() => {
      setPayoutState('settled');
      onPayoutApproved();
      alert(
        "Batch Payout Successful!\n\n• Mark Santos (Editor): $422.45 USD\n• Ana Silva (Designer): $300.00 USD\n• PayPal Outbound Fee: $1.00 USD (Estimate)\n• Double-entry journal legs posted to ledger."
      );
    }, 900);
  };

  return (
    <section>
      <div className="tab-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <span className="tag">Review Before Transfer</span>
            <h2>Staged Payouts</h2>
            <p className="tab-sub">
              Net deposit detected from PayPal capture. Review amounts and estimated fees before dispatching.
            </p>
          </div>
          <button onClick={handleSimulateWebhook} className="btn ghost sm">
            Simulate $2,500 Capture Webhook
          </button>
        </div>
      </div>

      <div className="panel-card" style={{ marginBottom: 20 }}>
        <div className="row">
          <div>
            <span className="tag">Incoming Capture</span>
            <div style={{ fontWeight: 700, fontSize: 15, marginTop: 2 }}>
              NordVPN Campaign — Milestone 1
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 12 }} className="mono">
              Capture ID: <span>CAP-2026-991A</span> · Net deposited:{' '}
              <b style={{ color: 'var(--text)' }}>$2,412.26 USD</b> (after $87.74 inbound fee)
            </div>
          </div>
          <div className="text-right">
            <span className={`badge ${payoutState === 'settled' ? 'b-ok' : 'b-warn'}`}>
              {payoutState === 'settled' ? 'Settled' : 'Staged for Review'}
            </span>
            <div className="mono" style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
              Hash: 7f8a91b2c...
            </div>
          </div>
        </div>

        <div className="table-container" style={{ marginTop: 16 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Role</th>
                <th>PayPal Account</th>
                <th>Share Rule</th>
                <th className="text-right">Net Amount</th>
                <th className="text-right">Arrival Time</th>
              </tr>
            </thead>
            <tbody className="mono">
              <tr>
                <td style={{ fontFamily: 'var(--font-body)', fontWeight: 600 }}>Ana Silva</td>
                <td style={{ fontFamily: 'var(--font-body)', color: 'var(--muted)' }}>Designer</td>
                <td>
                  designer-br@sandbox.com <span className="badge b-ok">Verified</span>
                </td>
                <td>Fixed priority</td>
                <td className="text-right"><b>$300.00</b></td>
                <td className="text-right">
                  <span className="badge b-warn">Estimate</span> Instant
                </td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-body)', fontWeight: 600 }}>Mark Santos</td>
                <td style={{ fontFamily: 'var(--font-body)', color: 'var(--muted)' }}>Editor</td>
                <td>
                  editor-ph@sandbox.com <span className="badge b-ok">Verified</span>
                </td>
                <td>20% of remainder</td>
                <td className="text-right"><b>$422.45</b></td>
                <td className="text-right">
                  <span className="badge b-warn">Estimate</span> 1-2 days
                </td>
              </tr>
              <tr style={{ background: 'var(--panel)' }}>
                <td style={{ fontFamily: 'var(--font-body)', fontWeight: 700 }}>
                  Apex Media (Creator)
                </td>
                <td style={{ fontFamily: 'var(--font-body)', color: 'var(--muted)' }}>Producer</td>
                <td>creator-biz@sandbox.com</td>
                <td>Remainder retained</td>
                <td className="text-right"><b>$1,689.81</b></td>
                <td className="text-right">Immediate</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="row" style={{ marginTop: 16, paddingTop: 12, borderBottom: 0 }}>
          <div style={{ fontSize: 12 }}>
            <span style={{ color: 'var(--muted)' }}>Parity check:</span>
            <b className="mono" style={{ marginLeft: 6 }}>
              $300.00 + $422.45 + $1,689.81 = $2,412.26
            </b>
            <span className="badge b-ok" style={{ marginLeft: 8 }}>Balanced</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: 'var(--muted)' }} className="mono">
              Est. batch fee: $1.00 USD <span className="badge b-warn">Estimate</span>
            </span>
            <button
              onClick={handleApprovePayout}
              disabled={payoutState !== 'staged'}
              className={`btn ${payoutState === 'settled' ? 'ghost' : ''}`}
            >
              {payoutState === 'staged' && 'Approve & Dispatch Payout'}
              {payoutState === 'dispatching' && 'Processing PayPal Payout...'}
              {payoutState === 'settled' && 'Dispatched via PayPal'}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

