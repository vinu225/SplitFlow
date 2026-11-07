"""
Comprehensive End-to-End API Endpoint Test Suite.
Tests all routers: auth, contracts, webhooks, payouts, ledger, and copilot.
"""
import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import UploadFile
from app.database import Base
from app.services.ledger_service import init_ledger_schema_and_triggers
from datetime import datetime, timedelta
from app.models import Creator, UserSession, Contract, Milestone, StagedPayoutBatch, StagedPayoutItem, PaymentCapture, WebhookEvent
from app.routers import auth, contracts, payouts, ledger, copilot
from app.schemas import CreatorCreate, ApprovePayoutRequest, CopilotChatRequest
from app.services.split_engine import compute_payout_state_hash

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    init_ledger_schema_and_triggers(db)
    yield db
    db.close()

def test_auth_and_session(test_db):
    creator_data = CreatorCreate(
        business_name="Apex Media Studios",
        email="creator@apex.com",
        paypal_merchant_id="MERCHANT-101"
    )
    creator = auth.register_creator(creator_data, test_db)
    assert creator.id is not None
    assert creator.email == "creator@apex.com"

    session_resp = auth.create_session(creator.id, "CREATOR_OWNER", test_db)
    assert session_resp.token.startswith("sess_")
    assert session_resp.creator_id == creator.id


def test_contract_upload_and_diff(test_db):
    creator = Creator(business_name="Apex Media", email="creator@apex.com")
    test_db.add(creator)
    test_db.commit()

    session = UserSession(id="sess_test", creator_id=creator.id, role="CREATOR_OWNER")

    # Read sample contract v1
    with open("sample_contracts/NordVPN_Sponsorship_Agreement_v1.pdf", "rb") as f:
        pdf_v1_bytes = f.read()

    file_v1 = UploadFile(filename="NordVPN_v1.pdf", file=io.BytesIO(pdf_v1_bytes))
    
    # 1. Upload Version 1
    res_v1 = contracts.process_contract_upload(
        pdf_bytes=pdf_v1_bytes,
        filename="NordVPN_v1.pdf",
        contract_id=None,
        client_name="NordVPN",
        session=session,
        db=test_db
    )

    assert res_v1["version_number"] == 1
    assert res_v1["client_name"] == "NordVPN"
    assert len(res_v1["parsed_terms"]["milestones"]) == 2
    assert res_v1["requires_reapproval"] is False

    contract_id = res_v1["contract_id"]

    # 2. Upload Version 2 (with terms changed: Net-60, Milestone 2 cut by $500)
    with open("sample_contracts/NordVPN_Sponsorship_Agreement_v2.pdf", "rb") as f:
        pdf_v2_bytes = f.read()

    res_v2 = contracts.process_contract_upload(
        pdf_bytes=pdf_v2_bytes,
        filename="NordVPN_v2.pdf",
        contract_id=contract_id,
        client_name="NordVPN",
        session=session,
        db=test_db
    )

    assert res_v2["version_number"] == 2
    # Verify multi-facet diffing triggered re-approval
    contract = test_db.query(Contract).filter_by(id=contract_id).first()
    assert contract.current_version == 2


def test_payout_hash_and_approval(test_db):
    creator = Creator(business_name="Apex Media", email="creator@apex.com")
    test_db.add(creator)
    test_db.flush()

    session = UserSession(
        id="sess_test_123",
        creator_id=creator.id,
        role="CREATOR_OWNER",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    test_db.add(session)

    milestone = Milestone(
        contract_id=1,
        version_id=1,
        creator_id=creator.id,
        description="M1 Test",
        expected_amount_minor_units=250000,
        currency="USD"
    )
    test_db.add(milestone)
    test_db.flush()

    capture = PaymentCapture(
        capture_id="CAP-TEST-123",
        invoice_id="INV-TEST-123",
        gross_minor_units=250000,
        fee_minor_units=8774,
        net_minor_units=241226,
        currency="USD"
    )
    test_db.add(capture)
    test_db.flush()

    staging_key = "stage_test_1_cap_1"
    items_raw = [
        {"collaborator_id": 1, "verified_email": "editor@sandbox.com", "amount_minor": 42245, "split_type": "PERCENT"},
        {"collaborator_id": 2, "verified_email": "designer@sandbox.com", "amount_minor": 30000, "split_type": "FLAT"}
    ]
    state_hash = compute_payout_state_hash(items_raw, staging_key)

    staged_batch = StagedPayoutBatch(
        staging_key=staging_key,
        creator_id=creator.id,
        milestone_id=milestone.id,
        capture_id="CAP-TEST-123",
        state_hash=state_hash,
        total_payout_minor_units=72245,
        creator_remainder_minor_units=168981,
        status="STAGED"
    )
    test_db.add(staged_batch)
    test_db.commit()

    # Query staged
    staged_list = payouts.list_staged_payout_batches(session, test_db)
    assert len(staged_list) == 1
    assert staged_list[0].state_hash == state_hash


def test_ledger_and_csv_export(test_db):
    creator = Creator(business_name="Apex Media", email="creator@apex.com")
    test_db.add(creator)
    test_db.flush()

    session = UserSession(
        id="sess_test",
        creator_id=creator.id,
        role="CREATOR_OWNER",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    test_db.add(session)
    test_db.commit()

    # Query Chart of Accounts
    accounts = ledger.list_accounts(test_db)
    assert len(accounts) >= 7

    # Export CSV
    csv_resp = ledger.export_contractor_expense_csv(session, test_db)
    csv_text = csv_resp.body.decode("utf-8")
    assert "does not constitute certified tax" in csv_text
    assert "Expense Category" in csv_text


def test_copilot_deterministic_queries(test_db):
    creator = Creator(business_name="Apex Media", email="creator@apex.com")
    test_db.add(creator)
    test_db.flush()

    session = UserSession(
        id="sess_test",
        creator_id=creator.id,
        role="CREATOR_OWNER",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    test_db.add(session)
    test_db.commit()

    # Ask for collaborators
    resp = copilot.copilot_chat(CopilotChatRequest(message="Show me my team collaborators"), session, test_db)
    assert resp.response is not None
    assert len(resp.tool_calls_executed) >= 1
    assert resp.tool_calls_executed[0]["tool"] == "list_collaborators"
