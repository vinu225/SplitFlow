import React from 'react';

interface SummaryStripProps {
  sowVersion: number;
}

export const SummaryStrip: React.FC<SummaryStripProps> = ({ sowVersion }) => {
  return (
    <div className="summary-strip">
      <div className="wrap summary-inner">
        <div className="stat-item">
          <span className="stat-label">Active SOW:</span>
          <b className="mono">
            {sowVersion === 1
              ? 'NordVPN Campaign ($5,000.00 USD)'
              : 'NordVPN Campaign ($4,500.00 USD amended)'}
          </b>
        </div>
        <div className="stat-item">
          <span className="stat-label">Verified Collaborators:</span>
          <b className="mono">3 in directory</b>
        </div>
        <div className="stat-item">
          <span className="stat-label">Ledger Parity:</span>
          <b className="mono" style={{ color: 'var(--ok)' }}>
            $0.00 Discrepancy
          </b>
        </div>
        <div className="stat-item">
          <span className="stat-label">System Mode:</span>
          <span className="badge b-warn">PayPal Sandbox Prototype</span>
        </div>
      </div>
    </div>
  );
};

