"""Verification requests, debt, and connector dispatch."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from packages.verify.connectors import VerificationConnectorService, VerificationStatus
from packages.verify.state_machine import get_next_retry_time
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, OFFICERS, require

router = APIRouter()


class VerifyIn(BaseModel):
    document_id: str
    route: str = "reference_lookup"
    issuer_path: str = "/issuers/noc/verify"
    institution_code: str = "SUNRISE-001"
    reference_number: str = "NOC-SYN-001"
    claimed_fields: dict = {}


def _debt(statuses: list[str]) -> int:
    return sum(1 for s in statuses if s in ("SOURCE_UNAVAILABLE", "VERIFICATION_PENDING", "CONSENT_REQUIRED"))


@router.get("/applications/{app_id}/verification")
def list_verification(app_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.id::text, r.document_id::text, r.route, r.issuer_id, r.status,
                   r.attempt_count, r.next_retry_at, r.ps_status, r.created_at
            FROM verification_requests r
            WHERE r.application_id = %s
            ORDER BY r.created_at DESC
            """,
            (str(app_id),),
        )
        reqs = rows_as_dicts(cur)
        statuses = [r.get("ps_status") or r.get("status") for r in reqs]
        return {
            "requests": reqs,
            "verification_debt": _debt(statuses),
            "synthetic_data": True,
        }


@router.post("/applications/{app_id}/verification")
def run_verification(app_id: UUID, body: VerifyIn, request: Request, user=require(*OFFICERS)):
    chaos = bool(getattr(request.app.state, "chaos", False))
    svc = VerificationConnectorService()
    if chaos:
        result = type("R", (), {})()
        # Force SOURCE_UNAVAILABLE when the demo chaos switch is on.
        from packages.verify.connectors import VerificationResult

        result = VerificationResult(
            route=body.route.upper(),
            status=VerificationStatus.SOURCE_UNAVAILABLE,
            issuer_name="ChaosSwitch",
            verified_at="now",
            details="Issuer returned 503 (demo chaos switch)",
            retry_recommended=True,
        )
    else:
        if body.route == "qr":
            result = svc.verify_qr_payload("TRUST:SYNTHETIC", "deadbeef")
        elif body.route == "signature":
            result = svc.verify_pdf_signature(b"%PDF-1.4 synthetic")
        elif body.route == "consented_fetch":
            result = svc.verify_consented_fetch(token=None)
        else:
            result = svc.verify_via_issuer_api(
                body.issuer_path, body.institution_code, body.reference_number, body.claimed_fields
            )

    with db(request, user, role="app_det") as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO verification_requests
                (document_id, application_id, route, issuer_id, status, attempt_count, next_retry_at, ps_status)
            VALUES (%s, %s, %s, %s, %s, 1, %s, %s)
            RETURNING id
            """,
            (
                body.document_id,
                str(app_id),
                body.route,
                result.issuer_name,
                result.status.value,
                get_next_retry_time(1) if result.retry_recommended else None,
                result.status.value,
            ),
        )
        req_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO verification_results (request_id, source, requested_at, responded_at, status, fields_compared)
            VALUES (%s, %s, NOW(), NOW(), %s, %s::jsonb)
            """,
            (str(req_id), result.route, result.status.value, "{}"),
        )
        if result.status == VerificationStatus.SOURCE_UNAVAILABLE:
            cur.execute(
                """
                INSERT INTO document_status (document_id, status, source)
                VALUES (%s, 'SOURCE_UNAVAILABLE', %s)
                """,
                (body.document_id, result.issuer_name),
            )
            cur.execute(
                """
                INSERT INTO findings (application_id, source_code, tier, result, reason, evidence, clause_ref)
                VALUES (%s, 'D13-source-unavailable', 2, 'UNKNOWN', %s, %s::jsonb, 'PLACEHOLDER')
                """,
                (
                    str(app_id),
                    result.details,
                    '{"status":"SOURCE_UNAVAILABLE"}',
                ),
            )
        audit(
            conn,
            user.username,
            "verification_attempt",
            {
                "application_id": str(app_id),
                "status": result.status.value,
                "route": result.route,
                "synthetic_data": True,
            },
        )
    return {
        "status": result.status.value,
        "details": result.details,
        "retry_recommended": result.retry_recommended,
        "synthetic_data": True,
        "unknown_never_rejects": result.status == VerificationStatus.SOURCE_UNAVAILABLE,
    }
