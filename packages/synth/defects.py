"""Must-tier defect injectors (D01-D08, D10-D13, D20, D21). Should-tier is deferred."""
from __future__ import annotations

from typing import Any

MUST_TIER = [
    ("D01", "missing_required_document", 1),
    ("D02", "missing_field", 1),
    ("D03", "expired_document", 1),
    ("D04", "date_inconsistency", 1),
    ("D05", "identifier_checksum_failure", 1),
    ("D06", "cross_document_name_mismatch", 1),
    ("D07", "intake_mismatch_vs_portal", 1),
    ("D08", "reused_document_hash", 1),
    ("D10", "signature_modified_after_signing", 2),
    ("D11", "unsigned_where_required", 2),
    ("D12", "issuer_mismatch", 2),
    ("D13", "source_outage", 2),
    ("D20", "unreadable_scan", 2),
    ("D21", "injected_instructions", 1),
]


def pick_defects(index: int, split: str) -> list[dict[str, Any]]:
    """Deterministic defect mix per application index. D21 has no finding effect (authority)."""
    if split == "canary":
        return []
    chosen = []
    n = 1 + (index % 3)
    for k in range(n):
        code, kind, tier = MUST_TIER[(index + k * 3) % len(MUST_TIER)]
        result = "UNKNOWN" if code in ("D13", "D20") else "FALSE"
        if code == "D21":
            result = "UNKNOWN"  # injected instructions never become a rejection
        chosen.append({"code": code, "kind": kind, "tier": tier, "result": result})
    return chosen


def finding_reason(code: str) -> str:
    return {
        "D01": "Required document type is absent from the application package.",
        "D02": "A mandatory field could not be extracted from the declared document.",
        "D03": "Document validity date is before the academic year start.",
        "D04": "Affidavit date conflicts with stamp-paper purchase date.",
        "D05": "Identifier failed structural/checksum validation (PAN structure / GSTIN check).",
        "D06": "Normalised institution name differs across documents.",
        "D07": "Declared intake does not match the mock portal master record.",
        "D08": "SHA-256 of this file matches another application document.",
        "D10": "Embedded signature byte range no longer covers the current file.",
        "D11": "Document type requires a signature and none was present.",
        "D12": "Claimed issuer does not match the certificate subject.",
        "D13": "Issuer endpoint returned 503. SOURCE_UNAVAILABLE. UNKNOWN is not FALSE.",
        "D20": "Dual extractors disagreed or the scan was unreadable. Evaluates to UNKNOWN.",
        "D21": "Prompt-injection text present; ignored by the deterministic engine (no effect).",
    }.get(code, "Synthetic must-tier defect.")
