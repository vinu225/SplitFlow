"""
Deterministic Copilot Router.
Processes natural language queries via ID-scoped tool calls over verified ledger data.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import get_current_session, UserSession
from app.schemas import CopilotChatRequest, CopilotChatResponse
from app.services.copilot_service import COPILOT_TOOL_DEFINITIONS, execute_copilot_tool
from app.models import Contract, Collaborator

router = APIRouter(prefix="/api/copilot", tags=["Copilot"])

@router.get("/tools")
def get_available_copilot_tools():
    """Returns available read-only tool schemas."""
    return COPILOT_TOOL_DEFINITIONS

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    req: CopilotChatRequest,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Evaluates user prompt, selects appropriate deterministic backend tools,
    and returns a verified financial answer with zero arithmetic hallucination.
    """
    creator_id = session.creator_id
    query_lower = req.message.lower().strip()
    tools_executed = []
    response_text = ""

    # 1. Check for Collaborator Queries
    if "collaborator" in query_lower or "team" in query_lower or "editor" in query_lower:
        result = execute_copilot_tool("list_collaborators", {}, creator_id, db)
        tools_executed.append({"tool": "list_collaborators", "result": result})
        collabs = result.get("collaborators", [])
        if collabs:
            lines = [f"• {c['name']} ({c['role']}) — PayPal: {c['verified_email']} [{c['currency']}]" for c in collabs]
            response_text = "Here are your active team collaborators:\n" + "\n".join(lines)
        else:
            response_text = "You currently have no active collaborators registered in your directory."

    # 2. Check for Risk Analysis
    elif "risk" in query_lower or "terms" in query_lower or "clause" in query_lower:
        # Find first contract
        contract = db.query(Contract).filter_by(creator_id=creator_id).first()
        if contract:
            result = execute_copilot_tool("analyze_contract_risk_terms", {"contract_id": contract.id}, creator_id, db)
            tools_executed.append({"tool": "analyze_contract_risk_terms", "result": result})
            risks = result.get("detected_risks", [])
            response_text = f"Contract Risk Assessment for {result.get('client_name')} (Risk Score: {result.get('risk_score')}):\n"
            response_text += "\n".join([f"⚠️ {r}" for r in risks])
        else:
            response_text = "No active contracts found to evaluate for risk terms."

    # 3. Check for Financial Summary / Net Profit Queries
    elif any(k in query_lower for k in ["net", "earn", "profit", "how much", "financial", "revenue", "paid"]):
        contract = db.query(Contract).filter_by(creator_id=creator_id).first()
        if contract:
            result = execute_copilot_tool("get_contract_financial_summary", {"contract_id": contract.id}, creator_id, db)
            tools_executed.append({"tool": "get_contract_financial_summary", "result": result})
            
            response_text = (
                f"Financial Summary for **{result.get('client_name')}** ({result.get('currency')}):\n"
                f"• Gross Invoiced: **${result.get('gross_revenue_formatted')}**\n"
                f"• Inbound PayPal Fees: **-${result.get('inbound_paypal_fees_formatted')}**\n"
                f"• Team Contractor Payouts: **-${result.get('contractor_payouts_formatted')}**\n"
                f"• Outbound Payout Fees: **-${result.get('outbound_payout_fees_formatted')}**\n"
                f"─────────────────────────────\n"
                f"• **Creator Net Retained Profit:** **${result.get('net_creator_profit_formatted')}**"
            )
        else:
            response_text = "No active contracts found to summarize financial records."

    # 4. Fallback General Prompt
    else:
        response_text = (
            "I am your SplitFlow Financial Copilot. I can query verified double-entry ledger data, "
            "inspect contract risk terms, list active collaborator directories, or summarize net project earnings. "
            "Try asking: 'What did I net after team payouts and fees?' or 'Evaluate contract risk terms'."
        )

    return CopilotChatResponse(
        response=response_text,
        tool_calls_executed=tools_executed
    )

