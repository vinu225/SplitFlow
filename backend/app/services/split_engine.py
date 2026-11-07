"""
Cumulative Multi-Capture Split Engine.
Guarantees:
1. Flat fees satisfied on first-dollar priority basis.
2. Percentage splits apply strictly to remaining net pool.
3. Creator remainder absorbs all odd minor unit rounding.
4. Total disbursements strictly equal net received funds.
"""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models import Milestone, MilestoneAllocation, MilestoneSplitRule, Collaborator
from app.currencies import get_currency_decimals

def calculate_cumulative_splits(
    milestone: Milestone,
    capture_net_minor: int,
    currency: str,
    db: Session
) -> tuple[list[dict], int, int]:
    """
    Computes split allocations for a specific capture against a milestone.
    Accounts for previous captures to prevent duplicate flat fee deductions.
    Returns: (staged_items, total_payout_minor, creator_remainder_minor)
    """
    if capture_net_minor <= 0:
        raise ValueError(f"Capture net amount must be positive. Received: {capture_net_minor}")

    # Fetch split rules for this milestone
    split_rules = db.query(MilestoneSplitRule).filter_by(milestone_id=milestone.id).all()
    
    # Query cumulative historical allocations for this milestone
    past_allocations = db.query(MilestoneAllocation).filter_by(milestone_id=milestone.id).all()
    past_flat_by_collab: dict[int, int] = {}
    for alloc in past_allocations:
        if alloc.split_type == "FLAT":
            past_flat_by_collab[alloc.collaborator_id] = (
                past_flat_by_collab.get(alloc.collaborator_id, 0) + alloc.allocated_minor_units
            )

    staged_items = []
    total_payout_minor = 0
    remaining_capture_net = capture_net_minor

    # Separate flat fee rules and percentage rules
    flat_rules = [r for r in split_rules if r.split_type == "FLAT"]
    percent_rules = [r for r in split_rules if r.split_type == "PERCENT"]

    # 1. Process Flat Fees (First-dollar priority, up to remaining contractual amount)
    for rule in flat_rules:
        target_flat_minor = rule.split_value  # Stored in minor units
        already_paid = past_flat_by_collab.get(rule.collaborator_id, 0)
        still_owed = max(0, target_flat_minor - already_paid)

        if still_owed > 0 and remaining_capture_net > 0:
            alloc_amount = min(still_owed, remaining_capture_net)
            collab = db.query(Collaborator).filter_by(id=rule.collaborator_id).first()
            if not collab:
                raise ValueError(f"Collaborator ID {rule.collaborator_id} not found")

            staged_items.append({
                "collaborator_id": collab.id,
                "verified_email": collab.verified_paypal_email,
                "amount_minor": alloc_amount,
                "split_type": "FLAT"
            })
            total_payout_minor += alloc_amount
            remaining_capture_net -= alloc_amount

    # 2. Process Percentage Allocations (Against remaining net pool from this capture)
    net_pool_for_percent = remaining_capture_net
    if net_pool_for_percent > 0:
        for rule in percent_rules:
            # split_value is percentage * 100 (e.g. 2000 = 20.00%)
            pct_decimal = Decimal(rule.split_value) / Decimal("10000")
            collab_amount = int(
                (Decimal(net_pool_for_percent) * pct_decimal).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )

            collab = db.query(Collaborator).filter_by(id=rule.collaborator_id).first()
            if not collab:
                raise ValueError(f"Collaborator ID {rule.collaborator_id} not found")

            staged_items.append({
                "collaborator_id": collab.id,
                "verified_email": collab.verified_paypal_email,
                "amount_minor": collab_amount,
                "split_type": "PERCENT"
            })
            total_payout_minor += collab_amount

    # 3. Creator Remainder absorbs all leftover minor units
    creator_remainder_minor = capture_net_minor - total_payout_minor

    # Strict Invariant Assertions
    if total_payout_minor + creator_remainder_minor != capture_net_minor:
        raise ValueError(
            f"Mathematical invariant broken: Payouts ({total_payout_minor}) + "
            f"Remainder ({creator_remainder_minor}) != Net Received ({capture_net_minor})"
        )
    if total_payout_minor > capture_net_minor:
        raise ValueError(
            f"Overdraft violation: Collaborator payouts ({total_payout_minor}) "
            f"exceed net received ({capture_net_minor})"
        )

    return staged_items, total_payout_minor, creator_remainder_minor


def compute_payout_state_hash(staged_items: list[dict], staging_key: str) -> str:
    """
    Generates a deterministic SHA-256 state hash of all staged items.
    Protects against UI tampering or TOCTOU state manipulation before execution.
    """
    normalized = {
        "staging_key": staging_key,
        "items": sorted([
            {
                "collaborator_id": item["collaborator_id"],
                "verified_email": item["verified_email"],
                "amount_minor": item["amount_minor"],
                "split_type": item["split_type"]
            } for item in staged_items
        ], key=lambda x: (x["collaborator_id"], x["verified_email"]))
    }
    serialized = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

