"""
Pydantic API Schemas for Request and Response Payloads.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime

# ============================================================================
# AUTH & CREATOR
# ============================================================================
class CreatorCreate(BaseModel):
    business_name: str
    email: EmailStr
    paypal_merchant_id: Optional[str] = None

class CreatorResponse(BaseModel):
    id: int
    business_name: str
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}

class SessionResponse(BaseModel):
    token: str
    creator_id: int
    role: str
    expires_at: datetime

# ============================================================================
# COLLABORATORS & PRESETS
# ============================================================================
class CollaboratorCreate(BaseModel):
    full_name: str
    role: str
    verified_paypal_email: EmailStr
    default_currency: str = "USD"

class CollaboratorResponse(BaseModel):
    id: int
    full_name: str
    role: str
    verified_paypal_email: str
    default_currency: str
    is_active: bool
    model_config = {"from_attributes": True}

class TeamSplitRuleInput(BaseModel):
    collaborator_id: int
    split_type: str  # 'FLAT' or 'PERCENT'
    split_value: int  # Flat minor units or percent * 100 (e.g. 2000 for 20%)

# ============================================================================
# CONTRACTS & MILESTONES
# ============================================================================
class MilestoneInput(BaseModel):
    description: str
    expected_amount_minor_units: int
    currency: str = "USD"
    due_date: Optional[str] = None
    split_rules: list[TeamSplitRuleInput] = []

class ContractParseResponse(BaseModel):
    contract_id: int
    version_number: int
    document_hash: str
    client_name: str
    parsed_terms: dict[str, Any]
    diff_summary: Optional[str] = None
    requires_reapproval: bool
    source_highlights: list[dict[str, Any]] = []

class GenerateInvoiceRequest(BaseModel):
    milestone_id: int
    client_email: EmailStr

# ============================================================================
# STAGED PAYOUTS & APPROVALS
# ============================================================================
class StagedItemResponse(BaseModel):
    id: int
    collaborator_id: int
    collaborator_name: str
    verified_email: str
    amount_minor_units: int
    amount_formatted: str
    currency: str
    split_type: str
    status: str

class StagedBatchResponse(BaseModel):
    staging_key: str
    milestone_id: int
    capture_id: str
    state_hash: str
    total_payout_minor_units: int
    total_payout_formatted: str
    creator_remainder_minor_units: int
    creator_remainder_formatted: str
    currency: str
    status: str
    items: list[StagedItemResponse]

class ApprovePayoutRequest(BaseModel):
    staging_key: str
    expected_state_hash: str

# ============================================================================
# COPILOT CHAT
# ============================================================================
class CopilotChatRequest(BaseModel):
    message: str

class CopilotChatResponse(BaseModel):
    response: str
    tool_calls_executed: list[dict[str, Any]] = []
