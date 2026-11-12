import Link from "next/link";

const DASHBOARD = "/dashboard";

export default function Landing() {
  return (
    <>
      <header className="top">
        <div className="wrap nav">
          <a className="logo" href="#top"><i />SplitFlow</a>
          <nav className="links">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#safety">Safety</a>
          </nav>
          <Link className="btn" href={DASHBOARD}>Open dashboard →</Link>
        </div>
      </header>

      <main>
        <div className="hero" id="top">
          <div className="hero-left">
            <span className="tag">Contracts → Invoices → Payouts</span>
            <h1>Turn sponsorship contracts into verified payouts.</h1>
            <p>
              Upload a brand contract, check every extracted number against its source clause,
              invoice through PayPal, and pay your team after one human approval.
            </p>
            <div className="cta">
              <Link className="btn" href={DASHBOARD}>Open dashboard →</Link>
              <a className="btn ghost" href="#how">See how it works</a>
            </div>
          </div>
          <div className="hero-right">
            <div className="panel-card">
              <span className="tag">Milestone 1 · Review</span>
              <div className="row"><span>Net received</span><b>$2,412.26</b></div>
              <div className="row"><span>Designer (flat)</span><b>$300.00</b></div>
              <div className="row"><span>Editor (20%)</span><b>$422.45</b></div>
              <div className="row"><span>Creator remainder</span><b>$1,689.81</b></div>
              <div className="row"><span>Source quote</span><span className="badge b-ok">Verified</span></div>
              <div className="quote">“50% due upon mutual signing”</div>
              <div className="row" style={{ marginTop: 8 }}>
                <span>Fees and timing</span><span className="badge b-warn">Estimate</span>
              </div>
            </div>
          </div>
        </div>

        <section className="block" id="how">
          <div className="wrap">
            <h2>How it works</h2>
            <div className="grid2">
              <div><h3>Read the contract</h3><p>AI extracts the client, milestones, and amounts. Each value is checked against the exact text it came from, and unmatched quotes are flagged for manual review.</p></div>
              <div><h3>Invoice with PayPal</h3><p>Confirmed milestones become PayPal invoices. Payment is detected by webhook, with the actual net amount read from the capture.</p></div>
              <div><h3>Split with plain arithmetic</h3><p>Shares are computed in code using integer cents. The AI never does the math, and any odd cents go to the creator.</p></div>
              <div><h3>Approve once, pay the team</h3><p>You review the staged payouts, then approve. The payout sent is exactly what you saw, locked by a state hash.</p></div>
            </div>
          </div>
        </section>
        <hr />
        <section className="block" id="features">
          <div className="wrap">
            <h2>What’s inside</h2>
            <div className="cards">
              <div><div className="tile"><span className="c1" /><span className="c2" /><strong>Source<br />check</strong></div><h3>Verified extraction</h3><p>Click a number, see the clause it came from.</p></div>
              <div><div className="tile warm"><span className="c1" /><span className="c3" /><strong>Staged<br />payouts</strong></div><h3>Human approval</h3><p>Per-recipient amounts and estimates before anything moves.</p></div>
              <div><div className="tile soft"><span className="c2" /><span className="c3" /><strong>Ledger<br />+ CSV</strong></div><h3>Clear records</h3><p>Ledger and contractor expense export. Not tax advice.</p></div>
            </div>
          </div>
        </section>
        <hr />
        <section className="block" id="safety">
          <div className="wrap">
            <h2>Built with guardrails</h2>
            <div className="grid2">
              <div><h3>Verified directory only</h3><p>Payout emails come from your saved collaborator list, never from document text.</p></div>
              <div><h3>Copilot reads, never writes</h3><p>Questions about earnings run through fixed ledger queries, so numbers aren’t guessed.</p></div>
            </div>
            <div className="note">This is a prototype running in the PayPal sandbox with test money. Fee and delivery figures are estimates, and exports are for record-keeping only.</div>
          </div>
        </section>
      </main>

      <footer className="foot"><div className="wrap">SplitFlow · sandbox prototype · MIT licensed</div></footer>
    </>
  );
}
