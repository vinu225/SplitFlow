# SplitFlow AI (v3.3)
### Autonomous Milestone & Cross-Border Payout Engine for Creators & Freelancers

> Built for the **"Build What's Next with PayPal and AI"** Global Hackathon.  
> Targeting: **Grand Prize**, **Best Use of Agentic Commerce**, and **Best Use of PayPal + AI**.

---

## 🌟 Overview

**SplitFlow AI** is an AI-assisted financial operations pipeline with human-in-the-loop governance designed for creators and independent agencies who manage cross-border teams. 

Instead of manual split calculations, spreadsheet errors, and unexpected PayPal fee deductions, SplitFlow:
1. **Parses SOW contracts** and highlights source clauses with verified character bounding boxes.
2. **Detects multi-facet contract changes** across 6 dimensions (Currency, Payment Terms, Milestones, Deadlines, Cancellation, Exclusivity) and triggers re-approval circuit breakers.
3. **Dispatches official milestone invoices** using the **PayPal Invoicing v2 API**.
4. **Ingests payments with 3-Level Atomic Idempotency**, traversing real `payments.transactions[]` and capture breakdowns.
5. **Calculates cumulative multi-capture splits in ISO 4217 minor units** (satisfying flat fees first, calculating percentages on remaining net, and allocating leftover units to the creator).
6. **Dispatches batch cross-border payouts** using the **PayPal Payouts API** with 30-day idempotent batch recovery and safe `RETURNED` item handling.
7. **Maintains an immutable double-entry financial ledger** with database triggers enforcing debits == credits, complete with a 1-click **Schedule-C Contractor Expense CSV export**.
8. **Provides a deterministic financial copilot** that queries ledger data via read-only ID lookups, eliminating financial hallucinations.

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SPLITFLOW WEB DASHBOARD                         │
│  • Side-by-Side PDF Viewer & Verbatim Source Bounding Box Highlighter      │
│  • Multi-Facet Contract Diff Viewer (Net-15 -> Net-60 Alert)                │
│  • Staged Payout Review Screen with Pre-Verified Directory Emails           │
│  • Immutable Double-Entry Ledger UI & Schedule-C CSV Exporter               │
│  • Deterministic Copilot Chat with Read-Only Tool Inspect                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST API (Bearer Auth)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND ENGINE (FastAPI)                          │
│  • PyMuPDF (fitz) Character & Bounding Box Extractor                        │
│  • Multi-Facet Deterministic Code Diff Engine                               │
│  • Three-Level Atomic Idempotency Webhook Gate                              │
│  • Multi-Currency Minor Unit (ISO 4217) Cumulative Split Engine             │
│  • PayPal Client: OAuth2, Invoicing v2, Captures v2, Payouts v1             │
│  • Two-Phase Ledger Posting with SQLite Balance Enforcement Trigger         │
└──────────────────────┬───────────────────────────────┬──────────────────────┘
                       │                               │
                       ▼                               ▼
       ┌───────────────────────────────┐   ┌───────────────────────────────┐
       │     LOCAL RELATIONAL DB       │   │      PAYPAL DEVELOPER API     │
       │    (SQLite / Foreign Keys)    │   │  • Invoicing API (v2)         │
       │ • contracts, contract_versions│   │  • Payouts Batch API (v1)     │
       │ • collaborators, presets      │   │  • Webhook Verification       │
       │ • journal_entries, legs       │   │  • Transaction Reporting      │
       └───────────────────────────────┘   └───────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* **Python 3.11+**
* Web browser (Chrome / Edge / Firefox)
* Optional: PayPal Sandbox Developer Account

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/SplitFlow-AI.git
cd SplitFlow-AI

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` in the `backend/` directory:
```bash
cp backend/.env.example backend/.env
```
Add your PayPal Sandbox `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` (optional for offline demo mode).

### 4. Run the Application
```bash
python run_splitflow.py
```
Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 🧪 Running the Verification Test Suite

SplitFlow includes an exhaustive automated test suite covering precision accounting, cumulative multi-capture splits, contract diffing, and double-entry ledger balance enforcement:

```bash
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest.exe backend\tests -v
```

---

## 🎮 3-Minute Demo Walkthrough (For Hackathon Judges)

1. **Contract Ingestion:**
   * Open the dashboard at `http://127.0.0.1:8000`.
   * Click **"Load Sample SOW v1 (Baseline)"**.
   * Observe the side-by-side view: clicking Milestone 1 highlights the verbatim clause in the document.
2. **PayPal Invoice Dispatch:**
   * Click **"Generate PayPal Invoice"**.
   * An official invoice is staged and linked to `INV2-NORD-991A`.
3. **Capture Simulation & Staged Review:**
   * Switch to Tab 2: **"Staged Payouts & Approval"**.
   * Click **"Simulate $2,500 Invoice Payment (Capture)"**.
   * Observe the decoupled traversal: net deposited is **$2,412.26** (after $87.74 inbound fee).
   * Notice that Ana Silva is allocated her **$300.00 flat fee** on a first-dollar basis, Mark Santos gets **20% of the remainder ($422.45)**, and the creator retains **$1,689.81**.
4. **Payout Execution & Immutable Ledger:**
   * Click **"Approve & Dispatch Batch Payout"**.
   * Batch is disbursed to collaborator emails and posted to the double-entry general ledger.
   * Switch to Tab 3: inspect the balanced journal entries (`DR 5030 / DR 5020 / CR 1010`) and click **"Download Schedule-C CSV Export"**.
5. **Contract Amendment Risk Diff:**
   * Switch back to Tab 1 and click **"Load SOW v2 (Net-60 Shift)"**.
   * The system immediately flags a **Cash Flow Risk Alert**: payment window shifted from Net-15 to Net-60 days and Milestone 2 was cut by $500. Automatic payout staging is locked until the creator accepts the amendment.
6. **Deterministic Copilot:**
   * Switch to Tab 4: click **"Calculate Net Retained Profit"**.
   * The Copilot executes `get_contract_financial_summary(contract_id=1)` and reports exact net profit ($1,688.81) with zero financial hallucination.

---

## 📄 License
MIT License. Open source for the PayPal & AI Developer Community.

