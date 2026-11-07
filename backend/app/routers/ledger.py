"""
Financial Ledger & Reporting Router.
Provides double-entry journal logs, chart of accounts, and Schedule-C CSV export.
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import JournalEntry, Account
from app.routers.auth import get_current_session, UserSession
from app.services.ledger_service import generate_contractor_expense_csv
from app.currencies import from_minor_units

router = APIRouter(prefix="/api/ledger", tags=["Ledger"])

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    """Returns Chart of Accounts."""
    accounts = db.query(Account).all()
    return [{"code": a.code, "name": a.name, "type": a.type} for a in accounts]

@router.get("/entries")
def list_journal_entries(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Returns posted double-entry journal entries and balanced legs for the creator."""
    entries = (
        db.query(JournalEntry)
        .filter_by(creator_id=session.creator_id, is_posted=True)
        .order_by(JournalEntry.posted_at.desc())
        .all()
    )

    result = []
    for e in entries:
        legs = []
        for l in e.legs:
            legs.append({
                "account_code": l.account_code,
                "account_name": l.account.name if l.account else "",
                "debit_minor_units": l.debit_minor_units,
                "debit_formatted": from_minor_units(l.debit_minor_units, e.currency),
                "credit_minor_units": l.credit_minor_units,
                "credit_formatted": from_minor_units(l.credit_minor_units, e.currency)
            })

        result.append({
            "id": e.id,
            "reference_id": e.reference_id,
            "currency": e.currency,
            "narration": e.narration,
            "posted_at": e.posted_at,
            "legs": legs
        })

    return result

@router.get("/export-csv")
def export_contractor_expense_csv(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Downloads audit-ready Schedule-C Contractor Expense CSV with explicit legal disclaimer.
    """
    csv_content = generate_contractor_expense_csv(db=db, creator_id=session.creator_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=splitflow_contractor_expenses_schedule_c.csv"}
    )

