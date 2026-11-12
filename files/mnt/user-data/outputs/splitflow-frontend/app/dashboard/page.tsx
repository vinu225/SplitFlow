import Link from "next/link";

// Placeholder. Replace with your real dashboard (contracts, payouts, ledger, copilot).
// Protect this route with your auth check before showing any financial data.
export default function Dashboard() {
  return (
    <div className="wrap" style={{ padding: "48px 24px", minHeight: "70vh" }}>
      <Link href="/" className="tag">← Back to landing</Link>
      <h2 style={{ marginTop: 14 }}>Dashboard</h2>
      <div className="dash-grid">
        <aside className="dash-side">
          <span className="tag">Navigation</span>
          <div className="row"><span>Contracts</span></div>
          <div className="row"><span>Payouts</span></div>
          <div className="row"><span>Ledger</span></div>
          <div className="row"><span>Copilot</span></div>
        </aside>
        <div className="dash-main">
          <p style={{ color: "var(--muted)" }}>Your dashboard goes here.</p>
        </div>
      </div>
    </div>
  );
}
