"""Institution portal: Tier 1/2 deficiencies, rectification, consent."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import require

router = APIRouter()


class RectifyIn(BaseModel):
    finding_id: str
    note: str = Field(..., min_length=3)


class ConsentIn(BaseModel):
    document_types: list[str]
    purpose: str
    days: int = 30


@router.get("/deficiencies")
def deficiencies(request: Request, user=require("institution_user")):
    if not user.institution_id:
        raise HTTPException(400, "No institution bound to this user")
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.id::text, f.application_id::text, f.source_code, f.tier, f.result,
                   f.reason, f.clause_ref, a.academic_year
            FROM findings f
            JOIN applications a ON a.id = f.application_id
            WHERE a.institution_id = %s AND f.tier <= 2
            ORDER BY f.created_at DESC
            """,
            (user.institution_id,),
        )
        return {"deficiencies": rows_as_dicts(cur), "synthetic_data": True}


@router.post("/rectify")
def rectify(body: RectifyIn, request: Request, user=require("institution_user")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reviewer_notes (finding_id, application_id, note_text, note_hash, user_id)
            SELECT %s, f.application_id, %s, %s, %s
            FROM findings f WHERE f.id = %s
            """,
            (body.finding_id, body.note, "rectify", user.sub, body.finding_id),
        )
        cur.execute(
            """
            INSERT INTO information_requests
                (application_id, requested_by, document_or_field, reason, due_at, state, answered_at)
            SELECT f.application_id, %s, %s, %s, NOW() + INTERVAL '7 days', 'ANSWERED', NOW()
            FROM findings f WHERE f.id = %s
            """,
            (user.sub, f"finding:{body.finding_id}", body.note, body.finding_id),
        )
        audit(conn, user.username, "rectification_submitted", {"finding_id": body.finding_id, "synthetic_data": True})
        return {"ok": True, "synthetic_data": True}


@router.get("/consent")
def list_consent(request: Request, user=require("institution_user", "scrutiny_officer", "sysadmin")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id::text, institution_id::text, document_types, purpose, expires_at, revoked_at, created_at
            FROM consent_artifacts
            ORDER BY created_at DESC
            """
        )
        return {"artifacts": rows_as_dicts(cur), "synthetic_data": True}


@router.post("/consent")
def grant_consent(body: ConsentIn, request: Request, user=require("institution_user")):
    if not user.institution_id:
        raise HTTPException(400, "No institution bound to this user")
    expires = datetime.now(timezone.utc) + timedelta(days=body.days)
    import json

    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO consent_artifacts (institution_id, granted_by, document_types, purpose, expires_at)
            VALUES (%s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (user.institution_id, user.sub, json.dumps(body.document_types), body.purpose, expires),
        )
        cid = cur.fetchone()[0]
        audit(conn, user.username, "consent_granted", {"consent_id": str(cid), "pkce": True, "synthetic_data": True})
        return {"consent_id": str(cid), "expires_at": expires.isoformat(), "synthetic_data": True}


@router.post("/consent/{consent_id}/revoke")
def revoke_consent(consent_id: UUID, request: Request, user=require("institution_user", "sysadmin")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE consent_artifacts SET revoked_at = NOW() WHERE id = %s", (str(consent_id),))
        audit(conn, user.username, "consent_revoked", {"consent_id": str(consent_id)})
        return {"ok": True, "synthetic_data": True}
