"""
Unit & Integration Test Suite for SplitFlow AI Core Engine.
Tests:
1. ISO 4217 minor unit precision & unsupported currency rejection.
2. Cumulative multi-capture split calculations & mathematical invariants.
3. Multi-facet contract diffing & risk assessment.
4. Double-entry balanced ledger posting & SQLite trigger enforcement.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.currencies import to_minor_units, from_minor_units, UnsupportedCurrencyError
from app.services.diff_engine import compute_complete_contract_diff
from app.services.ledger_service import (
    init_ledger_schema_and_triggers,
    post_balanced_journal_entry,
    UnbalancedJournalEntryError
)
from app.models import Creator, Collaborator, Milestone, MilestoneSplitRule
from app.services.split_engine import calculate_cumulative_splits

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    init_ledger_schema_and_triggers(db)
    yield db
    db.close()


def test_currency_minor_units():
    # 2 Decimals
    assert to_minor_units("2500.00", "USD") == 250000
    assert from_minor_units(250000, "USD") == "2500.00"

    # 0 Decimals (JPY)
    assert to_minor_units("50000", "JPY") == 50000
    assert from_minor_units(50000, "JPY") == "50000"

    # 3 Decimals (KWD)
    assert to_minor_units("12.500", "KWD") == 12500
    assert from_minor_units(12500, "KWD") == "12.500"

    # Rejection of unsupported currency
    with pytest.raises(UnsupportedCurrencyError):
        to_minor_units("100.00", "XYZ_FAKE_CURRENCY")


def test_cumulative_multi_capture_splits(test_db):
    creator = Creator(business_name="Test Creator", email="creator@test.com")
    test_db.add(creator)
    test_db.flush()

    collab_designer = Collaborator(
        creator_id=creator.id,
        full_name="Designer",
        role="Designer",
        verified_paypal_email="designer@test.com",
        default_currency="USD"
    )
    collab_editor = Collaborator(
        creator_id=creator.id,
        full_name="Editor",
        role="Editor",
        verified_paypal_email="editor@test.com",
        default_currency="USD"
    )
    test_db.add_all([collab_designer, collab_editor])
    test_db.flush()

    milestone = Milestone(
        contract_id=1,
        version_id=1,
        creator_id=creator.id,
        description="Milestone 1 Test",
        expected_amount_minor_units=250000,
        currency="USD"
    )
    test_db.add(milestone)
    test_db.flush()

    # Rules: $300 flat to designer (30000 cents), 20% to editor (2000)
    rule_flat = MilestoneSplitRule(milestone_id=milestone.id, collaborator_id=collab_designer.id, split_type="FLAT", split_value=30000)
    rule_pct = MilestoneSplitRule(milestone_id=milestone.id, collaborator_id=collab_editor.id, split_type="PERCENT", split_value=2000)
    test_db.add_all([rule_flat, rule_pct])
    test_db.commit()

    # Capture 1: $1,000 partial payment ($964.61 net = 96461 cents)
    items_c1, total_payout_c1, creator_rem_c1 = calculate_cumulative_splits(
        milestone=milestone,
        capture_net_minor=96461,
        currency="USD",
        db=test_db
    )

    # Designer gets $300 flat (30000 cents)
    # Remaining net for %: 96461 - 30000 = 66461 cents
    # Editor 20% on 66461: 13292 cents
    # Creator remainder: 96461 - 30000 - 13292 = 53169 cents
    assert total_payout_c1 == 30000 + 13292
    assert creator_rem_c1 == 53169
    assert total_payout_c1 + creator_rem_c1 == 96461


def test_double_entry_ledger_balance(test_db):
    creator = Creator(business_name="Ledger Test", email="ledger@test.com")
    test_db.add(creator)
    test_db.commit()

    # Balanced entry ($2,500 AR to Revenue)
    legs = [
        {"account_code": "1200", "debit_minor": 250000, "credit_minor": 0},
        {"account_code": "4010", "debit_minor": 0, "credit_minor": 250000}
    ]
    entry = post_balanced_journal_entry(
        db=test_db,
        creator_id=creator.id,
        reference_id="INV-TEST-001",
        currency="USD",
        narration="Test invoice issuance",
        legs=legs
    )
    assert entry.is_posted is True

    # Unbalanced entry must raise error
    unbalanced_legs = [
        {"account_code": "1010", "debit_minor": 100000, "credit_minor": 0},
        {"account_code": "4010", "debit_minor": 0, "credit_minor": 90000}
    ]
    with pytest.raises(UnbalancedJournalEntryError):
        post_balanced_journal_entry(
            db=test_db,
            creator_id=creator.id,
            reference_id="INV-UNBALANCED",
            currency="USD",
            narration="Should fail",
            legs=unbalanced_legs
        )


def test_contract_diff_detection():
    v1 = {
        "currency": "USD",
        "payment_terms_days": 15,
        "milestones": [
            {"milestone_number": 1, "description": "M1", "amount_minor_units": 250000, "due_date": "2026-11-15"},
            {"milestone_number": 2, "description": "M2", "amount_minor_units": 250000, "due_date": "2026-11-30"}
        ]
    }
    v2 = {
        "currency": "USD",
        "payment_terms_days": 60,  # Cash flow delay!
        "milestones": [
            {"milestone_number": 1, "description": "M1", "amount_minor_units": 250000, "due_date": "2026-11-15"},
            {"milestone_number": 2, "description": "M2", "amount_minor_units": 200000, "due_date": "2026-12-15"}  # Cut $500!
        ]
    }
    diff = compute_complete_contract_diff(v1, v2)
    assert diff["net_terms_changed"] is True
    assert diff["has_material_risk"] is True
    assert len(diff["milestones_modified"]) == 1
    assert diff["milestones_modified"][0]["new_minor_units"] == 200000

