"""
Decoupled PayPal Webhook Pipeline Router.
Implements:
1. Short DB Transaction 1: Status gating (handles retry of FAILED_RETRYABLE).
2. Decoupled Network I/O (no DB lock held during PayPal API calls).
3. Verified Capture Traversal (validates type == 'PAYPAL' and capture status == 'COMPLETED').
4. Short DB Transaction 2: Atomic capture, reconciliation & cumulative staging.
"""
import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from app.database import get_db
from app.models import WebhookEvent, PaymentCapture, Milestone, ReconciliationResult, StagedPayoutBatch, StagedPayoutItem
from app.services.paypal_client import paypal_client, PayPalAPIError
from app.services.split_engine import calculate_cumulative_splits, compute_payout_state_hash
from app.currencies import to_minor_units

logger = logging.getLogger("splitflow.webhooks")
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

@router.post("/paypal", status_code=status.HTTP_200_OK)
async def handle_paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
    paypal_auth_algo: str = Header(None, alias="paypal-auth-algo"),
    paypal_cert_url: str = Header(None, alias="paypal-cert-url"),
    paypal_transmission_id: str = Header(None, alias="paypal-transmission-id"),
    paypal_transmission_sig: str = Header(None, alias="paypal-transmission-sig"),
    paypal_transmission_time: str = Header(None, alias="paypal-transmission-time"),
):
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 1. Signature Verification (In-memory, no DB connection held)
    if paypal_transmission_sig:
        is_valid = paypal_client.verify_webhook_signature(
            transmission_id=paypal_transmission_id,
            transmission_time=paypal_transmission_time,
            cert_url=paypal_cert_url,
            auth_algo=paypal_auth_algo,
            transmission_sig=paypal_transmission_sig,
            raw_body=body_str
        )
        if not is_valid:
            logger.error("PayPal webhook signature verification failed.")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_id = payload.get("id")
    event_type = payload.get("event_type")

    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event ID")

    # =========================================================================
    # TRANSACTION 1: Quick Status Gate (~2ms)
    # =========================================================================
    should_process = False
    with db.begin():
        event = db.query(WebhookEvent).filter_by(event_id=event_id).with_for_update().first()

        if not event:
            # First time seeing event
            event = WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                status="PROCESSING",
                retry_count=0
            )
            db.add(event)
            should_process = True
        elif event.status == "PROCESSED":
            return {"status": "ignored", "reason": "already_processed"}
        elif event.status == "PROCESSING":
            return {"status": "in_flight", "reason": "concurrent_worker_active"}
        elif event.status in ["FAILED_RETRYABLE", "RECEIVED"]:
            event.status = "PROCESSING"
            event.retry_count += 1
            should_process = True
        else:  # FAILED_TERMINAL
            return {"status": "rejected", "reason": "terminal_failure"}

    if not should_process or event_type != "INVOICING.INVOICE.PAID":
        if event and event_type != "INVOICING.INVOICE.PAID":
            with db.begin():
                db.query(WebhookEvent).filter_by(event_id=event_id).update({"status": "PROCESSED"})
        return {"status": "ok", "reason": "non_invoice_event_processed"}

    # =========================================================================
    # EXTERNAL NETWORK I/O: NO DATABASE LOCK HELD (~300ms - 1500ms)
    # =========================================================================
    invoice_id = payload.get("resource", {}).get("invoice", {}).get("id")
    if not invoice_id:
        with db.begin():
            db.query(WebhookEvent).filter_by(event_id=event_id).update({
                "status": "FAILED_TERMINAL",
                "error_message": "Missing invoice ID in resource"
            })
        return {"status": "error", "reason": "missing_invoice_id"}

    verified_captures = []
    try:
        # Step A: Fetch invoice payment details
        invoice_data = paypal_client.get_invoice(invoice_id)
        payments = invoice_data.get("payments", {})
        transactions = payments.get("transactions", [])

        # Step B: Traverse transactions, check type == 'PAYPAL' and verify capture
        for tx in transactions:
            tx_type = tx.get("type")
            payment_id = tx.get("payment_id")

            if tx_type != "PAYPAL" or not payment_id:
                logger.info(f"Skipping non-PayPal or missing payment_id in invoice {invoice_id}")
                continue

            # Fetch capture details
            cap_data = paypal_client.get_capture(payment_id)
            if cap_data.get("status") != "COMPLETED":
                logger.warning(f"Capture {payment_id} status is {cap_data.get('status')}; skipping.")
                continue

            breakdown = cap_data.get("seller_receivable_breakdown", {})
            currency = breakdown.get("net_amount", {}).get("currency_code") or breakdown.get("net_amount", {}).get("currency", "USD")

            verified_captures.append({
                "capture_id": payment_id,
                "gross_minor": to_minor_units(breakdown.get("gross_amount", {}).get("value", "0.00"), currency),
                "fee_minor": to_minor_units(breakdown.get("paypal_fee", {}).get("value", "0.00"), currency),
                "net_minor": to_minor_units(breakdown.get("net_amount", {}).get("value", "0.00"), currency),
                "currency": currency
            })

    except Exception as exc:
        with db.begin():
            db.query(WebhookEvent).filter_by(event_id=event_id).update({
                "status": "FAILED_RETRYABLE",
                "error_message": f"PayPal API traversal error: {str(exc)}"
            })
        logger.error(f"External API error during webhook traversal: {exc}")
        return {"status": "retry_scheduled"}

    if not verified_captures:
        with db.begin():
            db.query(WebhookEvent).filter_by(event_id=event_id).update({
                "status": "PROCESSED",
                "error_message": "No valid PayPal captures found on invoice"
            })
        return {"status": "ok", "reason": "no_captures_found"}

    # =========================================================================
    # TRANSACTION 2: Atomic Persistence & Cumulative Staging (~5ms)
    # =========================================================================
    with db.begin():
        milestone = db.query(Milestone).filter_by(paypal_invoice_id=invoice_id).first()
        if not milestone:
            db.query(WebhookEvent).filter_by(event_id=event_id).update({
                "status": "PROCESSED",
                "error_message": "Orphan invoice not associated with SplitFlow milestone"
            })
            return {"status": "ok", "reason": "orphan_invoice"}

        for cap in verified_captures:
            # Level 2 Atomic Capture Deduplication
            stmt_l2 = (
                insert(PaymentCapture)
                .values(
                    capture_id=cap["capture_id"],
                    invoice_id=invoice_id,
                    gross_minor_units=cap["gross_minor"],
                    fee_minor_units=cap["fee_minor"],
                    net_minor_units=cap["net_minor"],
                    currency=cap["currency"]
                )
                .on_conflict_do_nothing(index_elements=["capture_id"])
            )
            res_l2 = db.execute(stmt_l2)
            if res_l2.rowcount == 0:
                continue

            # Reconciliation Check
            recon_status = "EXACT_MATCH" if cap["gross_minor"] == milestone.expected_amount_minor_units else "NEEDS_REVIEW"
            db.add(ReconciliationResult(
                capture_id=cap["capture_id"],
                milestone_id=milestone.id,
                status=recon_status,
                expected_minor_units=milestone.expected_amount_minor_units,
                actual_minor_units=cap["gross_minor"]
            ))

            # Cumulative Split Calculations
            staging_key = f"stage_{milestone.id}_{cap['capture_id']}"
            staged_items, total_payout_minor, creator_remainder_minor = calculate_cumulative_splits(
                milestone=milestone,
                capture_net_minor=cap["net_minor"],
                currency=cap["currency"],
                db=db
            )

            state_hash = compute_payout_state_hash(staged_items, staging_key)

            # Level 3 Atomic Staged Batch Persistence
            stmt_l3 = (
                insert(StagedPayoutBatch)
                .values(
                    staging_key=staging_key,
                    creator_id=milestone.creator_id,
                    milestone_id=milestone.id,
                    capture_id=cap["capture_id"],
                    state_hash=state_hash,
                    total_payout_minor_units=total_payout_minor,
                    creator_remainder_minor_units=creator_remainder_minor,
                    status="STAGED"
                )
                .on_conflict_do_nothing(index_elements=["staging_key"])
            )
            res_l3 = db.execute(stmt_l3)
            if res_l3.rowcount == 0:
                continue

            # Persist Staged Items
            for item in staged_items:
                db.add(StagedPayoutItem(
                    staging_key=staging_key,
                    collaborator_id=item["collaborator_id"],
                    sender_item_id=f"{staging_key}_{item['collaborator_id']}",
                    verified_email=item["verified_email"],
                    amount_minor_units=item["amount_minor"],
                    currency=cap["currency"]
                ))

        milestone.status = "PAID"
        db.query(WebhookEvent).filter_by(event_id=event_id).update({
            "status": "PROCESSED",
            "error_message": None
        })

    return {"status": "success", "invoice_id": invoice_id}

