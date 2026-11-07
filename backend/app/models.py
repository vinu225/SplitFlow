"""
SQLAlchemy Data Models for SplitFlow AI.
Enforces multi-tenant scoping, foreign keys, integer minor units, and audit trails.
"""
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

# ============================================================================
# 1. MULTI-TENANT CREATORS & SESSIONS
# ============================================================================
class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    paypal_merchant_id = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    contracts = relationship("Contract", back_populates="creator")
    collaborators = relationship("Collaborator", back_populates="creator")
    sessions = relationship("UserSession", back_populates="creator")
    presets = relationship("TeamSplitPreset", back_populates="creator")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(100), primary_key=True)  # Cryptographic session token
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    role = Column(String(50), default="CREATOR_OWNER", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    creator = relationship("Creator", back_populates="sessions")


# ============================================================================
# 2. CONTRACTS & MULTI-FACET VERSIONING
# ============================================================================
class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    client_name = Column(String(150), nullable=False)
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=utc_now)

    creator = relationship("Creator", back_populates="contracts")
    versions = relationship("ContractVersion", back_populates="contract")
    milestones = relationship("Milestone", back_populates="contract")


class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    document_hash = Column(String(64), nullable=False)
    raw_pdf_path = Column(String(255), nullable=False)
    parsed_terms = Column(JSON, nullable=False)
    diff_summary = Column(Text, nullable=True)
    requires_reapproval = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    contract = relationship("Contract", back_populates="versions")
    milestones = relationship("Milestone", back_populates="version")

    __table_args__ = (
        UniqueConstraint("contract_id", "document_hash", name="uq_contract_doc_hash"),
    )


# ============================================================================
# 3. COLLABORATORS & PRESETS
# ============================================================================
class Collaborator(Base):
    __tablename__ = "collaborators"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(100), nullable=False)
    verified_paypal_email = Column(String(255), nullable=False)
    default_currency = Column(String(10), default="USD", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    creator = relationship("Creator", back_populates="collaborators")

    __table_args__ = (
        UniqueConstraint("creator_id", "verified_paypal_email", name="uq_creator_collab_email"),
    )


class TeamSplitPreset(Base):
    __tablename__ = "team_split_presets"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    preset_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    creator = relationship("Creator", back_populates="presets")
    items = relationship("TeamSplitPresetItem", back_populates="preset")

    __table_args__ = (
        UniqueConstraint("creator_id", "preset_name", name="uq_creator_preset"),
    )


class TeamSplitPresetItem(Base):
    __tablename__ = "team_split_preset_items"

    id = Column(Integer, primary_key=True, index=True)
    preset_id = Column(Integer, ForeignKey("team_split_presets.id"), nullable=False)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=False)
    split_type = Column(String(20), nullable=False)  # 'FLAT' or 'PERCENT'
    split_value = Column(Integer, nullable=False)  # Flat in minor units or percent x100 (e.g. 2000 for 20.00%)

    preset = relationship("TeamSplitPreset", back_populates="items")
    collaborator = relationship("Collaborator")


# ============================================================================
# 4. MILESTONES & CUMULATIVE ALLOCATIONS
# ============================================================================
class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("contract_versions.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    description = Column(String(255), nullable=False)
    expected_amount_minor_units = Column(Integer, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    due_date = Column(DateTime, nullable=True)
    paypal_invoice_id = Column(String(100), unique=True, nullable=True, index=True)
    status = Column(String(50), default="PENDING", nullable=False)

    contract = relationship("Contract", back_populates="milestones")
    version = relationship("ContractVersion", back_populates="milestones")
    split_rules = relationship("MilestoneSplitRule", back_populates="milestone")
    allocations = relationship("MilestoneAllocation", back_populates="milestone")


class MilestoneSplitRule(Base):
    __tablename__ = "milestone_split_rules"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=False)
    split_type = Column(String(20), nullable=False)  # 'FLAT' or 'PERCENT'
    split_value = Column(Integer, nullable=False)  # Flat amount in minor units or percent * 100

    milestone = relationship("Milestone", back_populates="split_rules")
    collaborator = relationship("Collaborator")


class MilestoneAllocation(Base):
    __tablename__ = "milestone_allocations"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    capture_id = Column(String(100), nullable=False)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=False)
    split_type = Column(String(20), nullable=False)
    allocated_minor_units = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    milestone = relationship("Milestone", back_populates="allocations")
    collaborator = relationship("Collaborator")


# ============================================================================
# 5. ATOMIC IDEMPOTENCY & TRANSACTIONAL OUTBOX
# ============================================================================
class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id = Column(String(100), primary_key=True)  # L1: PayPal WH-XXXXX
    event_type = Column(String(100), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), nullable=False)  # 'RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED_RETRYABLE', 'FAILED_TERMINAL'
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class PaymentCapture(Base):
    __tablename__ = "payment_captures"

    capture_id = Column(String(100), primary_key=True)  # L2: PayPal CAP-XXXXX
    invoice_id = Column(String(100), nullable=False, index=True)
    gross_minor_units = Column(Integer, nullable=False)
    fee_minor_units = Column(Integer, nullable=False)
    net_minor_units = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=utc_now)


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(String(100), ForeignKey("payment_captures.capture_id"), unique=True, nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    status = Column(String(50), nullable=False)  # 'EXACT_MATCH', 'NEEDS_REVIEW'
    expected_minor_units = Column(Integer, nullable=False)
    actual_minor_units = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)


class StagedPayoutBatch(Base):
    __tablename__ = "staged_payout_batches"

    staging_key = Column(String(150), primary_key=True)  # L3: "stage_{milestone_id}_{capture_id}"
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    capture_id = Column(String(100), ForeignKey("payment_captures.capture_id"), nullable=False)
    state_hash = Column(String(64), nullable=False)
    total_payout_minor_units = Column(Integer, nullable=False)
    creator_remainder_minor_units = Column(Integer, nullable=False)
    sender_batch_id = Column(String(150), unique=True, nullable=True)
    status = Column(String(50), default="STAGED", nullable=False)  # 'STAGED', 'DISPATCHING', 'SUCCESS', 'FAILED'
    created_at = Column(DateTime, default=utc_now)

    items = relationship("StagedPayoutItem", back_populates="batch")


class StagedPayoutItem(Base):
    __tablename__ = "staged_payout_items"

    id = Column(Integer, primary_key=True, index=True)
    staging_key = Column(String(150), ForeignKey("staged_payout_batches.staging_key"), nullable=False)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=False)
    sender_item_id = Column(String(150), unique=True, nullable=False)
    verified_email = Column(String(255), nullable=False)
    amount_minor_units = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    payout_item_id = Column(String(100), nullable=True)
    status = Column(String(50), default="STAGED", nullable=False)  # 'STAGED', 'SUCCESS', 'FAILED', 'UNCLAIMED', 'RETURNED'

    batch = relationship("StagedPayoutBatch", back_populates="items")
    collaborator = relationship("Collaborator")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # 'PENDING', 'SENT', 'FAILED'
    created_at = Column(DateTime, default=utc_now)


class PayoutAttempt(Base):
    __tablename__ = "payout_attempts"

    id = Column(Integer, primary_key=True, index=True)
    staging_key = Column(String(150), ForeignKey("staged_payout_batches.staging_key"), nullable=False)
    sender_batch_id = Column(String(150), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    request_payload = Column(JSON, nullable=False)
    response_payload = Column(JSON, nullable=True)
    http_status = Column(Integer, nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow)


class ApprovalsAuditLog(Base):
    __tablename__ = "approvals_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    staging_key = Column(String(150), ForeignKey("staged_payout_batches.staging_key"), nullable=False)
    approved_by_session_id = Column(String(100), nullable=False)
    verified_state_hash = Column(String(64), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    approved_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 6. IMMUTABLE DOUBLE-ENTRY GENERAL LEDGER (MINOR UNITS)
# ============================================================================
class Account(Base):
    __tablename__ = "accounts"

    code = Column(String(10), primary_key=True)  # '1010', '1200', '2010', etc.
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # 'ASSET', 'LIABILITY', 'REVENUE', 'EXPENSE'

    legs = relationship("JournalLeg", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    reference_id = Column(String(100), nullable=False, index=True)
    currency = Column(String(10), nullable=False)
    narration = Column(Text, nullable=False)
    is_posted = Column(Boolean, default=False, nullable=False)
    posted_at = Column(DateTime, nullable=True)

    legs = relationship("JournalLeg", back_populates="journal_entry")


class JournalLeg(Base):
    __tablename__ = "journal_legs"

    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_code = Column(String(10), ForeignKey("accounts.code"), nullable=False)
    debit_minor_units = Column(Integer, default=0, nullable=False)
    credit_minor_units = Column(Integer, default=0, nullable=False)

    journal_entry = relationship("JournalEntry", back_populates="legs")
    account = relationship("Account", back_populates="legs")

    __table_args__ = (
        CheckConstraint("debit_minor_units >= 0", name="chk_debit_positive"),
        CheckConstraint("credit_minor_units >= 0", name="chk_credit_positive"),
    )
