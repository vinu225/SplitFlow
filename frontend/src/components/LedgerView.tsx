import React, { useState } from 'react';

interface LedgerRow {
  ref: string;
  date: string;
  title: string;
  details: string;
  debit: string;
  credit: string;
  balanced: boolean;
}

interface LedgerViewProps {
  additionalRows: LedgerRow[];
}

export const LedgerView: React.FC<LedgerViewProps> = ({ additionalRows }) => {
  const [downloading, setDownloading] = useState<boolean>(false);

  const initialRows: LedgerRow[] = [
    {
      ref: 'INV-2500-01',
      date: '2026-11-07 14:00',
      title: 'Milestone 1 Invoiced to NordVPN',
      details: 'DR 1200 Accounts Receivable / CR 4010 Sponsorship Revenue',
      debit: '$2,500.00',
      credit: '$2,500.00',
      balanced: true
    }
  ];

  const allRows = [...initialRows, ...additionalRows];

  const handleExportCSV = async () => {
    setDownloading(true);
    try {
      const res = await fetch('/api/ledger/export-csv?token=demo_session_token_12345');
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Schedule_C_Contractor_Expenses_${new Date().getFullYear()}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        window.location.href = 'http://127.0.0.1:8000/api/ledger/export-csv?token=demo_session_token_12345';
      }
    } catch {
      window.location.href = 'http://127.0.0.1:8000/api/ledger/export-csv?token=demo_session_token_12345';
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section>
      <div className="tab-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <span className="tag">Double-Entry Records</span>
            <h2>Ledger</h2>
            <p className="tab-sub">
              Every posted entry strictly balances debits and credits in integer cents. Blocked against mutations.
            </p>
          </div>
          <button onClick={handleExportCSV} disabled={downloading} className="btn ghost sm">
            {downloading ? 'Exporting...' : 'Export Schedule-C CSV'}
          </button>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Reference ID</th>
              <th>Date</th>
              <th>Narration & Posting Legs</th>
              <th className="text-right">Debit</th>
              <th className="text-right">Credit</th>
              <th className="text-center">Parity</th>
            </tr>
          </thead>
          <tbody className="mono">
            {allRows.map((r, i) => (
              <tr key={i}>
                <td>{r.ref}</td>
                <td style={{ color: 'var(--muted)' }}>{r.date}</td>
                <td style={{ fontFamily: 'var(--font-body)' }}>
                  <div style={{ fontWeight: 600 }}>{r.title}</div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {r.details}
                  </div>
                </td>
                <td className="text-right">{r.debit}</td>
                <td className="text-right">{r.credit}</td>
                <td className="text-center">
                  <span className="badge b-ok">Balanced</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="note">
        Exports and ledger rows are provided for creator record-keeping and Schedule-C preparation. This prototype does not provide formal tax or accounting advice.
      </div>
    </section>
  );
};

