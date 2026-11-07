"""
Payout Staging, Approval, PayPal Execution & Unclaimed Cancellation Router.
Enforces SHA-256 state hash validation, dynamic fee logging,
and safe retry semantics with double-entry ledger updates.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    StagedPayoutBatch, StagedPayoutItem, ApprovalsAuditLog, PayoutAttempt,
    Milestone, Collaborator
)
from app.routers.auth import get_current_session, UserSession
from app.schemas import ApprovePayoutRequest, StagedBatchResponse, StagedItemResponse
from app.services.paypal_client import paypal_client, PayPalAPIError
from app.services.ledger_service import post_balanced_journal_entry
from app.currencies import from_minor_units, to_minor_units

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])

@router.get("/staged", response_model=list[StagedBatchResponse])
def list_staged_payout_batches(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Lists all pending staged payout batches for the authenticated creator."""
    batches = (
        db.query(StagedPayoutBatch)
        .filter_by(creator_id=session.creator_id)
        .order_by(StagedPayoutBatch.created_at.desc())
        .all()
    )

    response = []
    for b in batches:
        milestone = db.query(Milestone).filter_by(id=b.milestone_id).first()
        currency = milestone.currency if milestone else "USD"

        items = []
        for it in b.items:
            collab = db.query(Collaborator).filter_by(id=it.collaborator_id).first()
            items.append(StagedItemResponse(
                id=it.id,
                collaborator_id=it.collaborator_id,
                collaborator_name=collab.full_name if collab else "Unknown",
                verified_email=it.verified_email,
                amount_minor_units=it.amount_minor_units,
                amount_formatted=from_minor_units(it.amount_minor_units, currency),
                currency=currency,
                split_type="SPLIT",
                status=it.status
            ))

        response.append(StagedBatchResponse(
            staging_key=b.staging_key,
            milestone_id=b.milestone_id,
            capture_id=b.capture_id,
            state_hash=b.state_hash,
            total_payout_minor_units=b.total_payout_minor_units,
            total_payout_formatted=from_minor_units(b.total_payout_minor_units, currency),
            creator_remainder_minor_units=b.creator_remainder_minor_units,
            creator_remainder_formatted=from_minor_units(b.creator_remainder_minor_units, currency),
            currency=currency,
            status=b.status,
            items=items
        ))

    return response


@router.post("/approve")
def approve_and_dispatch_payout_batch(
    req: ApprovePayoutRequest,
    request: Request,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Verifies the SHA-256 state hash, logs the audit record,
    dispatches the batch to PayPal with 30-day idempotent sender_batch_id,
    and commits balanced double-entry ledger entries.
    """
    creator_id = session.creator_id

    # 1. Fetch batch under lock
    batch = (
        db.query(StagedPayoutBatch)
        .filter_by(staging_key=req.staging_key, creator_id=creator_id)
        .with_for_update()
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Staged batch not found")

    if batch.status != "STAGED":
        raise HTTPException(status_code=400, detail=f"Batch cannot be dispatched from status: {batch.status}")

    # 2. Cryptographic State Hash Verification (TOCTOU protection)
    if batch.state_hash != req.expected_state_hash:
        raise HTTPException(
            status_code=409,
            detail="State Hash Mismatch: Staged terms changed on server since review was rendered."
        )

    # 3. Write Approvals Audit Log
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    audit = ApprovalsAuditLog(
        creator_id=creator_id,
        staging_key=batch.staging_key,
        approved_by_session_id=session.id,
        verified_state_hash=batch.state_hash,
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)
    batch.status = "DISPATCHING"
    db.commit()

    # 4. Build PayPal Batch Payload with unique sender_batch_id & sender_item_id
    milestone = db.query(Milestone).filter_by(id=batch.milestone_id).first()
    currency = milestone.currency if milestone else "USD"
    sender_batch_id = f"{batch.staging_key}_try_1"

    payout_items = []
    for item in batch.items:
        amount_str = from_minor_units(item.amount_minor_units, currency)
        payout_items.append({
            "recipient_type": "EMAIL",
            "amount": {
                "value": amount_str,
                "currency": currency
            },
            "receiver": item.verified_email,
            "note": f"SplitFlow Settlement for Milestone {milestone.id}",
            "sender_item_id": item.sender_item_id
        })

    payload = {
        "sender_batch_header": {
            "sender_batch_id": sender_batch_id,
            "email_subject": f"SplitFlow Payout: Settlement for {milestone.description}",
            "email_message": "You have received a collaborator payout from your project team via SplitFlow."
        },
        "items": payout_items
    }

    # 5. Dispatch to PayPal (outside DB transaction lock)
    try:
        payout_response = paypal_client.create_batch_payout(payload)
        paypal_batch_id = payout_response.get("batch_header", {}).get("payout_batch_id")
        
        # Read dynamic outbound fee from PayPal response if provided, otherwise default to 0
        fees_data = payout_response.get("batch_header", {}).get("fees", {})
        fee_value = fees_data.get("value", "0.00") if fees_data else "0.00"
        outbound_fee_minor = to_minor_units(fee_value, currency)

        # 6. Commit Success, Update Items & Post Ledger
        with db.begin():
            batch.sender_batch_id = sender_batch_id
            batch.status = "SUCCESS"

            for it in batch.items:
                it.status = "SUCCESS"

            # Log Payout Attempt
            db.add(PayoutAttempt(
                staging_key=batch.staging_key,
                sender_batch_id=sender_batch_id,
                attempt_number=1,
                request_payload=payload,
                response_payload=payout_response,
                http_status=201
            ))

            # POST DOUBLE-ENTRY LEDGER:
            # Leg A: DR 5030 Contractor Payout Expense
            # Leg B: DR 5020 PayPal Outbound Payout Fees
            # Leg C: CR 1010 PayPal Cash Balance
            total_disbursed_minor = batch.total_payout_minor_units + outbound_fee_minor
            legs = [
                {"account_code": "5030", "debit_minor": batch.total_payout_minor_units, "credit_minor": 0},
                {"account_code": "5020", "debit_minor": outbound_fee_minor, "credit_minor": 0},
                {"account_code": "1010", "debit_minor": 0, "credit_minor": total_disbursed_minor}
            ]

            post_balanced_journal_entry(
                db=db,
                creator_id=creator_id,
                reference_id=f"PAYOUT-{batch.staging_key}",
                currency=currency,
                narration=f"Dispatched batch payout {sender_batch_id} to {len(batch.items)} collaborators.",
                legs=legs
            )

        return {
            "status": "SUCCESS",
            "staging_key": batch.staging_key,
            "sender_batch_id": sender_batch_id,
            "paypal_batch_id": paypal_batch_id,
            "total_disbursed_formatted": from_minor_units(total_disbursed_minor, currency),
            "currency": currency
        }

    except PayPalAPIError as e:
        with db.begin():
            batch.status = "FAILED"
            db.add(PayoutAttempt(
                staging_key=batch.staging_key,
                sender_batch_id=sender_batch_id,
                attempt_number=1,
                request_payload=payload,
                response_payload={"error": str(e)},
                http_status=e.status_code
            ))
        raise HTTPException(status_code=500, detail=f"PayPal Payouts execution failed: {str(e)}")


@router.post("/items/{item_id}/cancel-unclaimed")
def cancel_unclaimed_item(
    item_id: int,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Cancels an unclaimed payout item.
    Confirms PayPal returns terminal status 'RETURNED' before updating ledger.
    """
    item = db.query(StagedPayoutItem).filter_by(id=item_id).first()
    if not item or not item.payout_item_id:
        raise HTTPException(status_code=404, detail="Payout item not found or missing PayPal item ID")

    try:
        # Call PayPal cancellation endpoint
        cancel_resp = paypal_client.cancel_unclaimed_payout_item(item.payout_item_id)
        returned_status = cancel_resp.get("transaction_status")

        if returned_status != "RETURNED":
            raise HTTPException(
                status_code=400,
                detail=f"Item cancellation did not achieve RETURNED status (Status: {returned_status})"
            )

        # Update status and post reversing entry
        with db.begin():
            item.status = "RETURNED"

            # Post reversing entry returning funds to Cash Balance
            legs = [
                {"account_code": "1010", "debit_minor": item.amount_minor_units, "credit_minor": 0},
                {"account_code": "5030", "debit_minor": 0, "credit_minor": item.amount_minor_units}
            ]
            post_balanced_journal_entry(
                db=db,
                creator_id=session.creator_id,
                reference_id=f"REVERSE-{item.sender_item_id}",
                currency=item.currency,
                narration=f"Reversed unclaimed payout for recipient {item.verified_email} back to cash balance.",
                legs=legs
            )

        return {"status": "RETURNED", "message": "Unclaimed item safely canceled and funds returned to ledger."}

    except PayPalAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"PayPal cancellation failed: {str(e)}")

