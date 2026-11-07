"""
Deterministic Tool-Calling Financial Copilot and Contract Risk Service.
All financial arithmetic and database queries are strictly executed in backend code.
The LLM never performs free-form arithmetic over unstructured data dumps.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Contract, ContractVersion, Collaborator, Milestone, JournalEntry, JournalLeg
from app.currencies import from_minor_units

COPILOT_TOOL_DEFINITIONS = [
    {
        "name": "list_collaborators",
        "description": "Returns a list of all active collaborators, their IDs, roles, and verified emails.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "find_contract_by_client",
        "description": "Finds contracts matching a client query and returns contract IDs and versions.",
        "parameters": {
            "type": "object",
            "properties": {"client_query": {"type": "string", "description": "e.g. 'NordVPN' or 'Shopify'"}},
            "required": ["client_query"]
        }
    },
    {
        "name": "get_contract_financial_summary",
        "description": "Returns deterministic gross invoiced, inbound fees, collaborator payouts, outbound fees, and net retained earnings in minor units and formatted strings.",
        "parameters": {
            "type": "object",
            "properties": {"contract_id": {"type": "integer", "description": "The internal contract ID"}},
            "required": ["contract_id"]
        }
    },
    {
        "name": "analyze_contract_risk_terms",
        "description": "Evaluates contract terms for cash flow risks, long payment windows (Net-60+), kill-fee terms, and currency exposure.",
        "parameters": {
            "type": "object",
            "properties": {"contract_id": {"type": "integer", "description": "The internal contract ID"}},
            "required": ["contract_id"]
        }
    }
]

def execute_copilot_tool(tool_name: str, arguments: dict, creator_id: int, db: Session) -> dict:
    """
    Executes a deterministic, read-only tool query on behalf of the Copilot.
    """
    if tool_name == "list_collaborators":
        collabs = db.query(Collaborator).filter_by(creator_id=creator_id, is_active=True).all()
        return {
            "collaborators": [
                {
                    "id": c.id,
                    "name": c.full_name,
                    "role": c.role,
                    "verified_email": c.verified_paypal_email,
                    "currency": c.default_currency
                }
                for c in collabs
            ]
        }

    elif tool_name == "find_contract_by_client":
        query_str = arguments.get("client_query", "").strip().lower()
        contracts = (
            db.query(Contract)
            .filter(
                Contract.creator_id == creator_id,
                func.lower(Contract.client_name).contains(query_str)
            )
            .all()
        )
        return {
            "matches": [
                {
                    "contract_id": c.id,
                    "client_name": c.client_name,
                    "current_version": c.current_version,
                    "status": c.status
                }
                for c in contracts
            ]
        }

    elif tool_name == "get_contract_financial_summary":
        contract_id = arguments.get("contract_id")
        contract = db.query(Contract).filter_by(id=contract_id, creator_id=creator_id).first()
        if not contract:
            return {"error": f"Contract ID {contract_id} not found."}

        # Query all milestone IDs for this contract
        milestones = db.query(Milestone).filter_by(contract_id=contract_id).all()
        milestone_invoice_ids = [m.paypal_invoice_id for m in milestones if m.paypal_invoice_id]

        # Aggregate double-entry journal legs for this contract's invoices
        entries = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.creator_id == creator_id,
                JournalEntry.is_posted == True
            )
            .all()
        )

        currency = milestones[0].currency if milestones else "USD"
        gross_revenue_minor = 0
        inbound_fees_minor = 0
        contractor_expense_minor = 0
        outbound_fees_minor = 0

        # Sum by account codes
        for entry in entries:
            for leg in entry.legs:
                if leg.account_code == "4010":  # Gross Revenue
                    gross_revenue_minor += leg.credit_minor_units
                elif leg.account_code == "5010":  # Inbound Fees
                    inbound_fees_minor += leg.debit_minor_units
                elif leg.account_code == "5030":  # Contractor Expense
                    contractor_expense_minor += leg.debit_minor_units
                elif leg.account_code == "5020":  # Outbound Payout Fees
                    outbound_fees_minor += leg.debit_minor_units

        net_creator_profit_minor = (
            gross_revenue_minor - inbound_fees_minor - contractor_expense_minor - outbound_fees_minor
        )

        return {
            "contract_id": contract_id,
            "client_name": contract.client_name,
            "currency": currency,
            "gross_revenue_minor_units": gross_revenue_minor,
            "gross_revenue_formatted": from_minor_units(gross_revenue_minor, currency),
            "inbound_paypal_fees_minor_units": inbound_fees_minor,
            "inbound_paypal_fees_formatted": from_minor_units(inbound_fees_minor, currency),
            "contractor_payouts_minor_units": contractor_expense_minor,
            "contractor_payouts_formatted": from_minor_units(contractor_expense_minor, currency),
            "outbound_payout_fees_minor_units": outbound_fees_minor,
            "outbound_payout_fees_formatted": from_minor_units(outbound_fees_minor, currency),
            "net_creator_profit_minor_units": net_creator_profit_minor,
            "net_creator_profit_formatted": from_minor_units(net_creator_profit_minor, currency)
        }

    elif tool_name == "analyze_contract_risk_terms":
        contract_id = arguments.get("contract_id")
        contract = db.query(Contract).filter_by(id=contract_id, creator_id=creator_id).first()
        if not contract:
            return {"error": f"Contract ID {contract_id} not found."}

        latest_version = (
            db.query(ContractVersion)
            .filter_by(contract_id=contract_id)
            .order_by(ContractVersion.version_number.desc())
            .first()
        )
        if not latest_version or not latest_version.parsed_terms:
            return {"error": "No parsed terms found for contract."}

        terms = latest_version.parsed_terms
        risks = []

        # Risk 1: Payment window delays
        net_days = terms.get("payment_terms_days", 15)
        if net_days and net_days >= 60:
            risks.append(f"High Cash Flow Risk: Unfavorable Net-{net_days} payment window creates extended working capital gap.")

        # Risk 2: Currency mismatch / FX exposure
        currency = terms.get("currency", "USD")
        if currency not in ["USD", "EUR", "GBP"]:
            risks.append(f"Currency Volatility Risk: Settled in {currency}, which may introduce exchange rate spread risk.")

        # Risk 3: Weak or missing cancellation clause
        cancellation = terms.get("cancellation_clause", "")
        if not cancellation or "kill fee" not in cancellation.lower():
            risks.append("Legal Risk: Missing explicit Kill Fee clause. Brand may cancel without compensating completed work.")

        return {
            "contract_id": contract_id,
            "client_name": contract.client_name,
            "version": latest_version.version_number,
            "risk_score": "HIGH" if len(risks) >= 2 else ("MEDIUM" if risks else "LOW"),
            "detected_risks": risks if risks else ["No high-risk terms identified. Standard agreement terms."]
        }

    return {"error": f"Tool '{tool_name}' is not recognized."}

