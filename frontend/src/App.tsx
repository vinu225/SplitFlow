import React, { useState } from 'react';
import { Header } from './components/Header';
import { SummaryStrip } from './components/SummaryStrip';
import { ContractsView } from './components/ContractsView';
import { StagedPayoutsView } from './components/StagedPayoutsView';
import { LedgerView } from './components/LedgerView';
import { CopilotView } from './components/CopilotView';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('contracts');
  const [sowVersion, setSowVersion] = useState<number>(1);
  const [stagedCount, setStagedCount] = useState<number>(0);
  const [additionalLedgerRows, setAdditionalLedgerRows] = useState<any[]>([]);

  const handleInvoiceCreated = () => {
    setStagedCount(1);
  };

  const handlePayoutApproved = () => {
    setStagedCount(0);
    setAdditionalLedgerRows([
      {
        ref: 'CAP-2026-991A',
        date: '2026-11-07 14:05',
        title: 'PayPal Invoice Payment Cleared (Gross: $2,500.00, Fee: $87.74, Net: $2,412.26)',
        details: 'DR 1010 Cash ($2,412.26) / DR 5010 Fee ($87.74) / CR 1200 AR ($2,500.00)',
        debit: '$2,500.00',
        credit: '$2,500.00',
        balanced: true
      },
      {
        ref: 'PAYOUT-STAGE-01',
        date: '2026-11-07 14:06',
        title: 'Dispatched Batch Payout: Editor ($422.45), Designer ($300.00), Outbound Fee ($1.00)',
        details: 'DR 5030 Contractor Expense ($722.45) / DR 5020 Payout Fee ($1.00) / CR 1010 Cash ($723.45)',
        debit: '$723.45',
        credit: '$723.45',
        balanced: true
      }
    ]);
  };

  return (
    <>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stagedCount={stagedCount}
        sowVersion={sowVersion}
        setSowVersion={setSowVersion}
      />

      <SummaryStrip sowVersion={sowVersion} />

      <main className="wrap" style={{ paddingBottom: 40 }}>
        {activeTab === 'contracts' && (
          <ContractsView
            sowVersion={sowVersion}
            onInvoiceCreated={handleInvoiceCreated}
          />
        )}

        {activeTab === 'staging' && (
          <StagedPayoutsView onPayoutApproved={handlePayoutApproved} />
        )}

        {activeTab === 'ledger' && (
          <LedgerView additionalRows={additionalLedgerRows} />
        )}

        {activeTab === 'copilot' && <CopilotView />}
      </main>

      <footer className="foot">
        <div className="wrap" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>SplitFlow · sandbox prototype · MIT licensed</div>
          <div>Record-keeping only · Not tax advice</div>
        </div>
      </footer>
    </>
  );
}

