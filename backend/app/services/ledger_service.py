"""
Immutable Double-Entry Ledger Service.
Enforces multi-currency balanced journal entries, prevents mutations,
and generates audit-ready Schedule-C Contractor Expense CSV reports.
"""
import io
import csv
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Account, JournalEntry, JournalLeg
from app.currencies import from_minor_units

# Standard Chart of Accounts Seed Data
DEFAULT_ACCOUNTS = [
    ("1010", "PayPal Cash Balance", "ASSET"),
    ("1200", "Accounts Receivable", "ASSET"),
    ("2010", "Collaborator Payouts Payable", "LIABILITY"),
    ("4010", "Gross Sponsorship Revenue", "REVENUE"),
    ("5010", "PayPal Inbound Processing Fees", "EXPENSE"),
    ("5020", "PayPal Outbound Payout Fees", "EXPENSE"),
    ("5030", "Contractor Payout Expense", "EXPENSE"),
]

class UnbalancedJournalEntryError(ValueError):
    """Raised when a journal entry's debits do not equal its credits."""
    pass

class LedgerImmutabilityError(RuntimeError):
    """Raised when an illegal update or delete is attempted on posted ledger records."""
    pass

def init_ledger_schema_and_triggers(db: Session):
    """
    Seeds default Chart of Accounts and sets up SQLite balance verification & immutability triggers.
    """
    # 1. Seed Accounts if not present
    for code, name, acc_type in DEFAULT_ACCOUNTS:
        existing = db.query(Account).filter_by(code=code).first()
        if not existing:
            db.add(Account(code=code, name=name, type=acc_type))
    db.commit()

    # 2. Apply SQLite triggers for balance enforcement and immutability (as individual standalone statements)
    trigger_statements = [
        """
        CREATE TRIGGER IF NOT EXISTS verify_journal_entry_balance_on_post
        BEFORE UPDATE OF is_posted ON journal_entries
        FOR EACH ROW
        WHEN NEW.is_posted = 1 AND OLD.is_posted = 0
        BEGIN
            SELECT CASE
                WHEN (
                    SELECT COALESCE(SUM(debit_minor_units), 0) - COALESCE(SUM(credit_minor_units), 0)
                    FROM journal_legs
                    WHERE journal_entry_id = NEW.id
                ) != 0
                THEN RAISE(ABORT, 'Financial Integrity Violation: Journal entry debits and credits do not balance.')
                
                WHEN (
                    SELECT COUNT(*)
                    FROM journal_legs
                    WHERE journal_entry_id = NEW.id
                ) < 2
                THEN RAISE(ABORT, 'Double-Entry Violation: Journal entry must contain at least two journal legs.')
            END;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prevent_journal_entries_update
        BEFORE UPDATE ON journal_entries
        FOR EACH ROW
        WHEN OLD.is_posted = 1
        BEGIN
            SELECT RAISE(ABORT, 'Journal entries are immutable once posted. Post a reversing entry.');
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prevent_journal_entries_delete
        BEFORE DELETE ON journal_entries
        FOR EACH ROW
        WHEN OLD.is_posted = 1
        BEGIN
            SELECT RAISE(ABORT, 'Journal entries are immutable. Deletions not permitted.');
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prevent_journal_legs_update
        BEFORE UPDATE ON journal_legs
        BEGIN
            SELECT RAISE(ABORT, 'Journal legs are immutable. Post a reversing entry.');
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS prevent_journal_legs_delete
        BEFORE DELETE ON journal_legs
        BEGIN
            SELECT RAISE(ABORT, 'Journal legs are immutable. Deletions not permitted.');
        END;
        """
    ]

    for stmt in trigger_statements:
        clean_stmt = stmt.strip()
        if clean_stmt:
            db.execute(text(clean_stmt))
    db.commit()


def post_balanced_journal_entry(
    db: Session,
    creator_id: int,
    reference_id: str,
    currency: str,
    narration: str,
    legs: list[dict]  # list of {"account_code": str, "debit_minor": int, "credit_minor": int}
) -> JournalEntry:
    """
    Posts an atomic, balanced double-entry journal entry.
    Validates debits == credits in application code before activating the database trigger.
    """
    total_debit = sum(leg.get("debit_minor", 0) for leg in legs)
    total_credit = sum(leg.get("credit_minor", 0) for leg in legs)

    if total_debit != total_credit:
        raise UnbalancedJournalEntryError(
            f"Unbalanced journal entry {reference_id}: Total Debits ({total_debit}) != Total Credits ({total_credit})"
        )
    if len(legs) < 2:
        raise UnbalancedJournalEntryError(
            f"Journal entry {reference_id} must have at least 2 legs. Provided: {len(legs)}"
        )

    # Step 1: Create unposted journal entry
    entry = JournalEntry(
        creator_id=creator_id,
        reference_id=reference_id,
        currency=currency.upper(),
        narration=narration,
        is_posted=False
    )
    db.add(entry)
    db.flush()

    # Step 2: Add legs
    for leg in legs:
        db.add(JournalLeg(
            journal_entry_id=entry.id,
            account_code=leg["account_code"],
            debit_minor_units=leg.get("debit_minor", 0),
            credit_minor_units=leg.get("credit_minor", 0)
        ))
    db.flush()

    # Step 3: Post entry (activates the verify_journal_entry_balance_on_post trigger)
    entry.is_posted = True
    entry.posted_at = datetime.utcnow()
    db.flush()
    return entry


def generate_contractor_expense_csv(db: Session, creator_id: int) -> str:
    """
    Generates a Schedule-C Contractor Expense CSV report for accounting & record-keeping.
    Includes explicit disclaimer: 'For record-keeping purposes only. Not certified tax advice.'
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Disclaimer Header
    writer.writerow(["# NOTICE: For internal record-keeping and Schedule C expense documentation only."])
    writer.writerow(["# This document does not constitute certified tax, legal, or accounting advice. Consult a CPA."])
    writer.writerow([])

    # CSV Column Headers
    writer.writerow([
        "Entry ID", "Posting Date (UTC)", "Reference ID", "Currency",
        "Account Code", "Account Name", "Expense Category",
        "Debit Amount", "Credit Amount", "Narration"
    ])

    # Query expense legs (Accounts 5010, 5020, 5030)
    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.creator_id == creator_id, JournalEntry.is_posted == True)
        .order_by(JournalEntry.posted_at.asc())
        .all()
    )

    for entry in entries:
        for leg in entry.legs:
            if leg.account_code in ["5010", "5020", "5030"]:
                category = "Contractor Payout" if leg.account_code == "5030" else "PayPal Platform Fee"
                debit_str = from_minor_units(leg.debit_minor_units, entry.currency) if leg.debit_minor_units else "0.00"
                credit_str = from_minor_units(leg.credit_minor_units, entry.currency) if leg.credit_minor_units else "0.00"

                writer.writerow([
                    entry.id,
                    entry.posted_at.strftime("%Y-%m-%d %H:%M:%S") if entry.posted_at else "",
                    entry.reference_id,
                    entry.currency,
                    leg.account_code,
                    leg.account.name if leg.account else "",
                    category,
                    debit_str,
                    credit_str,
                    entry.narration
                ])

    return output.getvalue()
