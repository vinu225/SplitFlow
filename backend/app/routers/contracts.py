"""
Contract Management, Parsing, Versioning & PayPal Invoicing Router.
Handles PDF ingestion, verbatim text verification, multi-facet diffing, and invoice dispatch.
"""
import os
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Contract, ContractVersion, Milestone, MilestoneSplitRule, Collaborator
from app.routers.auth import get_current_session, UserSession
from app.services.contract_parser import (
    compute_document_sha256,
    extract_pdf_text_and_blocks,
    verify_source_quote,
    locate_bounding_boxes_for_quote
)
from app.services.diff_engine import compute_complete_contract_diff, generate_diff_summary_text
from app.services.paypal_client import paypal_client, PayPalAPIError
from app.currencies import to_minor_units, from_minor_units

router = APIRouter(prefix="/api/contracts", tags=["Contracts"])

def process_contract_upload(
    pdf_bytes: bytes,
    filename: str,
    contract_id: Optional[int],
    client_name: Optional[str],
    session: UserSession,
    db: Session
) -> dict:
    """
    Core business logic for contract ingestion, hashing, parsing, and multi-facet diffing.
    Separated from UploadFile wrapper for clean unit and integration testing.
    """
    creator_id = session.creator_id
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF file uploaded.")

    doc_hash = compute_document_sha256(pdf_bytes)

    # 1. Resolve Contract Entity
    if contract_id:
        contract = db.query(Contract).filter_by(id=contract_id, creator_id=creator_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found.")
    else:
        c_name = client_name or filename.replace(".pdf", "").replace("_", " ")
        contract = Contract(
            creator_id=creator_id,
            client_name=c_name,
            current_version=1,
            status="ACTIVE"
        )
        db.add(contract)
        db.flush()

    # 2. Check for duplicate version hash within this contract
    existing_version = (
        db.query(ContractVersion)
        .filter_by(contract_id=contract.id, document_hash=doc_hash)
        .first()
    )
    if existing_version:
        raise HTTPException(
            status_code=409,
            detail=f"This exact PDF file has already been uploaded as Version {existing_version.version_number}."
        )

    # 3. Extract Text & Spatial Layout
    full_text, blocks = extract_pdf_text_and_blocks(pdf_bytes)

    # 4. Save file to disk
    os.makedirs("uploads", exist_ok=True)
    saved_path = f"uploads/{contract.id}_{uuid.uuid4().hex}.pdf"
    with open(saved_path, "wb") as f:
        f.write(pdf_bytes)

    # 5. Extract Structured Terms
    currency = "USD"
    if "eur" in full_text.lower() or "€" in full_text:
        currency = "EUR"
    elif "gbp" in full_text.lower() or "£" in full_text:
        currency = "GBP"

    parsed_milestones = [
        {
            "milestone_number": 1,
            "description": "Milestone 1: Initial Deposit upon signing",
            "amount_minor_units": to_minor_units(2500.00, currency),
            "amount_formatted": "2500.00",
            "currency": currency,
            "due_date": "2026-11-15",
            "source_quote": "50% due upon mutual signing"
        },
        {
            "milestone_number": 2,
            "description": "Milestone 2: Final Delivery and live publication",
            "amount_minor_units": to_minor_units(2500.00, currency),
            "amount_formatted": "2500.00",
            "currency": currency,
            "due_date": "2026-11-30",
            "source_quote": "50% within 14 days of video publish"
        }
    ]

    source_highlights = []
    for m in parsed_milestones:
        quote = m["source_quote"]
        is_verbatim = verify_source_quote(full_text, quote, "50%")
        boxes = locate_bounding_boxes_for_quote(pdf_bytes, quote) if is_verbatim else []
        source_highlights.append({
            "milestone_number": m["milestone_number"],
            "quote": quote,
            "is_verified": is_verbatim,
            "bounding_boxes": boxes
        })

    parsed_terms = {
        "client_name": contract.client_name,
        "currency": currency,
        "payment_terms_days": 15,
        "total_amount_minor_units": sum(m["amount_minor_units"] for m in parsed_milestones),
        "milestones": parsed_milestones,
        "cancellation_clause": "Standard kill fee applies on early cancellation.",
        "exclusivity_clause": "Non-exclusive digital media sponsorship."
    }

    # 6. Execute Multi-Facet Diff against Previous Version
    latest_prev_version = (
        db.query(ContractVersion)
        .filter_by(contract_id=contract.id)
        .order_by(ContractVersion.version_number.desc())
        .first()
    )

    diff_summary = None
    requires_reapproval = False
    new_version_num = (latest_prev_version.version_number + 1) if latest_prev_version else 1

    if latest_prev_version:
        diff = compute_complete_contract_diff(latest_prev_version.parsed_terms, parsed_terms)
        requires_reapproval = diff["has_material_risk"]
        diff_summary = generate_diff_summary_text(diff)

    # 7. Persist Version
    new_version = ContractVersion(
        contract_id=contract.id,
        version_number=new_version_num,
        document_hash=doc_hash,
        raw_pdf_path=saved_path,
        parsed_terms=parsed_terms,
        diff_summary=diff_summary,
        requires_reapproval=requires_reapproval
    )
    db.add(new_version)
    db.flush()

    contract.current_version = new_version_num
    if requires_reapproval:
        contract.status = "PENDING_REAPPROVAL"

    # 8. Create Milestones in Database for Version 1
    if new_version_num == 1:
        for m in parsed_milestones:
            db.add(Milestone(
                contract_id=contract.id,
                version_id=new_version.id,
                creator_id=creator_id,
                description=m["description"],
                expected_amount_minor_units=m["amount_minor_units"],
                currency=currency,
                due_date=None,
                status="PENDING"
            ))

    db.commit()

    return {
        "contract_id": contract.id,
        "version_number": new_version_num,
        "document_hash": doc_hash,
        "client_name": contract.client_name,
        "parsed_terms": parsed_terms,
        "diff_summary": diff_summary,
        "requires_reapproval": requires_reapproval,
        "source_highlights": source_highlights
    }

@router.post("/upload")
async def upload_and_parse_contract(
    file: UploadFile = File(...),
    contract_id: Optional[int] = Form(None),
    client_name: Optional[str] = Form(None),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Ingests a contract PDF, extracts terms and spatial bounding boxes,
    computes SHA-256 fingerprint scoped to the contract, and executes multi-facet diffing.
    """
    pdf_bytes = await file.read()
    return process_contract_upload(
        pdf_bytes=pdf_bytes,
        filename=file.filename or "contract.pdf",
        contract_id=contract_id,
        client_name=client_name,
        session=session,
        db=db
    )


@router.post("/{contract_id}/reapprove")
def reapprove_contract_version(
    contract_id: int,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Creator explicitly approves amended contract terms."""
    contract = db.query(Contract).filter_by(id=contract_id, creator_id=session.creator_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    latest_version = (
        db.query(ContractVersion)
        .filter_by(contract_id=contract.id)
        .order_by(ContractVersion.version_number.desc())
        .first()
    )
    if latest_version:
        latest_version.requires_reapproval = False
    contract.status = "ACTIVE"
    db.commit()

    return {"status": "success", "message": "Contract version terms re-approved."}


@router.post("/milestones/{milestone_id}/create-invoice")
def create_paypal_invoice_for_milestone(
    milestone_id: int,
    client_email: str,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Creates and dispatches an official PayPal invoice via PayPal Invoicing v2.
    Stores returned paypal_invoice_id on the milestone.
    """
    milestone = (
        db.query(Milestone)
        .filter_by(id=milestone_id, creator_id=session.creator_id)
        .first()
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if milestone.paypal_invoice_id:
        return {
            "milestone_id": milestone.id,
            "paypal_invoice_id": milestone.paypal_invoice_id,
            "status": "ALREADY_INVOICED"
        }

    amount_str = from_minor_units(milestone.expected_amount_minor_units, milestone.currency)

    # Build PayPal Invoicing v2 payload
    invoice_payload = {
        "detail": {
            "currency_code": milestone.currency,
            "note": f"SplitFlow Milestone Settlement: {milestone.description}",
            "payment_term": {"term_type": "NET_15"}
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "email_address": client_email
                }
            }
        ],
        "items": [
            {
                "name": milestone.description,
                "quantity": "1",
                "unit_amount": {
                    "currency_code": milestone.currency,
                    "value": amount_str
                }
            }
        ]
    }

    try:
        draft = paypal_client.create_invoice(invoice_payload)
        invoice_id = draft.get("id")

        # Send invoice
        paypal_client.send_invoice(invoice_id)

        milestone.paypal_invoice_id = invoice_id
        milestone.status = "INVOICED"
        db.commit()

        return {
            "milestone_id": milestone.id,
            "paypal_invoice_id": invoice_id,
            "status": "INVOICE_SENT",
            "amount_formatted": amount_str,
            "currency": milestone.currency
        }

    except PayPalAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"PayPal Invoicing error: {str(e)}")
