"""Verification Debt Calculator.

Principles:
1. UNKNOWN is not FALSE — unverified documents do not cause rejection.
2. Instead, unverified dependencies accrue 'Verification Debt'.
3. Debt tracks statutory uncertainty and missing authoritative corroboration.
4. When chaos mode causes issuer outages (503), debt rises in real-time.

Weights:
- Land / Title deed: 25 pts (Critical)
- Building plan approval: 20 pts (Critical)
- Fire safety NOC: 15 pts (High)
- Affidavit & Stamp paper: 15 pts (High)
- Faculty cadre list: 15 pts (Medium)
- Fee structure / FDR: 10 pts (Medium)

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from packages.verify.connectors import VerificationStatus

DOC_WEIGHTS = {
    "land_documents": 25.0,
    "trust_deed": 25.0,
    "building_plan": 20.0,
    "fire_safety_certificate": 15.0,
    "affidavit": 15.0,
    "stamp_paper": 10.0,
    "faculty_list": 15.0,
    "bank_statement": 10.0,
    "fee_structure": 10.0,
    "noc": 15.0,
}


@dataclass
class DebtBreakdownItem:
    doc_type: str
    status: str
    weight: float
    debt_incurred: float
    reason: str


@dataclass
class VerificationDebtReport:
    total_debt: float          # 0.0 to 100.0 (normalized)
    debt_tier: str             # LOW (0-20), MEDIUM (21-50), HIGH (51-75), CRITICAL (76-100)
    items: list[DebtBreakdownItem]
    verified_count: int
    unverified_count: int
    synthetic: bool = True
    clause_ref_placeholder: str = "PLACEHOLDER"


def calculate_verification_debt(documents: list[dict[str, Any]]) -> VerificationDebtReport:
    """Calculate verification debt based on status of application documents."""
    total_possible_weight = 0.0
    incurred_debt_weight = 0.0
    breakdown = []
    verified_cnt = 0
    unverified_cnt = 0

    for doc in documents:
        doc_type = doc.get("type_declared", "general")
        status = doc.get("status", "UNVERIFIED")
        weight = DOC_WEIGHTS.get(doc_type, 10.0)
        total_possible_weight += weight

        if status == VerificationStatus.VERIFIED.value:
            verified_cnt += 1
            incurred = 0.0
            reason = "Authoritatively verified"
        elif status == VerificationStatus.SOURCE_UNAVAILABLE.value:
            unverified_cnt += 1
            incurred = weight * 0.85
            reason = "Source unavailable (transient issuer outage / chaos mode)"
        elif status == VerificationStatus.CONSENT_REQUIRED.value:
            unverified_cnt += 1
            incurred = weight * 0.90
            reason = "Pending applicant consent authorization"
        elif status == VerificationStatus.NOT_IN_JURISDICTION.value:
            unverified_cnt += 1
            incurred = weight * 0.50
            reason = "Issuer outside digital verification jurisdiction"
        elif status == "UNREADABLE":
            unverified_cnt += 1
            incurred = weight
            reason = "Document unreadable or corrupted"
        else:  # UNVERIFIED or FAILED
            unverified_cnt += 1
            incurred = weight
            reason = "Unverified or pending corroboration"

        incurred_debt_weight += incurred
        breakdown.append(
            DebtBreakdownItem(
                doc_type=doc_type,
                status=status,
                weight=weight,
                debt_incurred=round(incurred, 1),
                reason=reason,
            )
        )

    # Normalize to 0-100 scale
    total_debt = round((incurred_debt_weight / total_possible_weight * 100.0), 1) if total_possible_weight > 0 else 0.0

    if total_debt <= 20:
        tier = "LOW"
    elif total_debt <= 50:
        tier = "MEDIUM"
    elif total_debt <= 75:
        tier = "HIGH"
    else:
        tier = "CRITICAL"

    return VerificationDebtReport(
        total_debt=total_debt,
        debt_tier=tier,
        items=breakdown,
        verified_count=verified_cnt,
        unverified_count=unverified_cnt,
    )
