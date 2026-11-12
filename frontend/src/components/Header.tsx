import React from 'react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  stagedCount: number;
  sowVersion: number;
  setSowVersion: (v: number) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  stagedCount,
  sowVersion,
  setSowVersion
}) => {
  return (
    <header className="top">
      <div className="wrap nav">
        <div className="logo" onClick={() => setActiveTab('contracts')}>
          <i aria-hidden="true" />SplitFlow
        </div>

        <nav className="nav-tabs" aria-label="Dashboard views">
          <button
            onClick={() => setActiveTab('contracts')}
            className={`nav-tab ${activeTab === 'contracts' ? 'active' : ''}`}
          >
            Contracts
          </button>
          <button
            onClick={() => setActiveTab('staging')}
            className={`nav-tab ${activeTab === 'staging' ? 'active' : ''}`}
          >
            Payouts{' '}
            {stagedCount > 0 && (
              <span className="badge b-warn" style={{ marginLeft: 4 }}>
                {stagedCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('ledger')}
            className={`nav-tab ${activeTab === 'ledger' ? 'active' : ''}`}
          >
            Ledger
          </button>
          <button
            onClick={() => setActiveTab('copilot')}
            className={`nav-tab ${activeTab === 'copilot' ? 'active' : ''}`}
          >
            Copilot
          </button>
        </nav>

        <div className="nav-actions">
          <button
            onClick={() => setSowVersion(1)}
            className={`btn ghost sm ${sowVersion === 1 ? 'active-sow' : ''}`}
          >
            SOW v1
          </button>
          <button
            onClick={() => setSowVersion(2)}
            className={`btn ghost sm ${sowVersion === 2 ? 'active-sow' : ''}`}
          >
            SOW v2
          </button>
          <span className="badge b-ok mono" title="Connected to PayPal Developer Sandbox">
            SANDBOX OK
          </span>
        </div>
      </div>
    </header>
  );
};

