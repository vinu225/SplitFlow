"""
Deterministic Multi-Facet Contract Diff Engine.
Compares contractual terms across 6 distinct dimensions:
1. Currency Delta
2. Payment Terms (Net-N days)
3. Milestone Amounts
4. Delivery Deadlines
5. Cancellation Clauses
6. Exclusivity Clauses
"""
from typing import Any

def compute_complete_contract_diff(v_prev: dict[str, Any], v_next: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministically computes differences between two parsed contract term sets.
    The output is used directly to determine whether re-approval is required,
    and is passed to the LLM to generate the human-readable diff narrative.
    """
    prev_currency = (v_prev.get("currency") or "USD").upper()
    next_currency = (v_next.get("currency") or "USD").upper()

    prev_net_terms = v_prev.get("payment_terms_days")
    next_net_terms = v_next.get("payment_terms_days")

    prev_cancellation = v_prev.get("cancellation_clause") or ""
    next_cancellation = v_next.get("cancellation_clause") or ""

    prev_exclusivity = v_prev.get("exclusivity_clause") or ""
    next_exclusivity = v_next.get("exclusivity_clause") or ""

    diff: dict[str, Any] = {
        "currency_changed": prev_currency != next_currency,
        "prev_currency": prev_currency,
        "next_currency": next_currency,
        "net_terms_changed": prev_net_terms != next_net_terms,
        "prev_net_terms_days": prev_net_terms,
        "next_net_terms_days": next_net_terms,
        "milestones_modified": [],
        "milestones_added": [],
        "milestones_removed": [],
        "deadlines_shifted": [],
        "cancellation_terms_altered": prev_cancellation.strip() != next_cancellation.strip(),
        "exclusivity_altered": prev_exclusivity.strip() != next_exclusivity.strip(),
        "has_material_risk": False
    }

    # Map milestones by milestone index / number
    prev_milestones = {m.get("milestone_number", idx + 1): m for idx, m in enumerate(v_prev.get("milestones", []))}
    next_milestones = {m.get("milestone_number", idx + 1): m for idx, m in enumerate(v_next.get("milestones", []))}

    # Check modified and added milestones
    for m_num, m_new in next_milestones.items():
        if m_num not in prev_milestones:
            diff["milestones_added"].append(m_new)
        else:
            m_old = prev_milestones[m_num]
            amount_changed = m_new.get("amount_minor_units") != m_old.get("amount_minor_units")
            date_changed = m_new.get("due_date") != m_old.get("due_date")

            if amount_changed:
                diff["milestones_modified"].append({
                    "milestone_number": m_num,
                    "description": m_new.get("description", ""),
                    "old_minor_units": m_old.get("amount_minor_units"),
                    "new_minor_units": m_new.get("amount_minor_units")
                })

            if date_changed:
                diff["deadlines_shifted"].append({
                    "milestone_number": m_num,
                    "description": m_new.get("description", ""),
                    "old_due_date": m_old.get("due_date"),
                    "new_due_date": m_new.get("due_date")
                })

    # Check removed milestones
    for m_num, m_old in prev_milestones.items():
        if m_num not in next_milestones:
            diff["milestones_removed"].append(m_old)

    # Determine whether material risk exists (requiring explicit human re-approval)
    diff["has_material_risk"] = bool(
        diff["currency_changed"] or
        diff["net_terms_changed"] or
        diff["milestones_modified"] or
        diff["milestones_added"] or
        diff["milestones_removed"] or
        diff["cancellation_terms_altered"]
    )

    return diff


def generate_diff_summary_text(diff: dict[str, Any]) -> str:
    """
    Generates a deterministic summary of contractual changes.
    Can be used directly or provided as grounding context to the LLM.
    """
    if not diff.get("has_material_risk"):
        return "No material financial or contractual changes detected between versions."

    points = []
    if diff.get("currency_changed"):
        points.append(f"Currency changed from {diff['prev_currency']} to {diff['next_currency']}.")

    if diff.get("net_terms_changed"):
        points.append(f"Payment terms shifted from Net-{diff['prev_net_terms_days']} to Net-{diff['next_net_terms_days']} days.")

    for m in diff.get("milestones_modified", []):
        points.append(
            f"Milestone {m['milestone_number']} ({m['description']}) amount modified: "
            f"{m['old_minor_units']} -> {m['new_minor_units']} minor units."
        )

    for m in diff.get("deadlines_shifted", []):
        points.append(
            f"Milestone {m['milestone_number']} ({m['description']}) deadline changed: "
            f"{m['old_due_date']} -> {m['new_due_date']}."
        )

    for m in diff.get("milestones_added", []):
        points.append(f"New milestone added: #{m.get('milestone_number')} ({m.get('description')}).")

    for m in diff.get("milestones_removed", []):
        points.append(f"Milestone removed: #{m.get('milestone_number')} ({m.get('description')}).")

    if diff.get("cancellation_terms_altered"):
        points.append("Cancellation / kill-fee clauses have been modified.")

    if diff.get("exclusivity_altered"):
        points.append("Exclusivity / non-compete terms have been altered.")

    return " | ".join(points)

