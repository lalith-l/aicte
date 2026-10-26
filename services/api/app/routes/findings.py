"""Findings (read) and reviewer actions (accept/dismiss). Models cannot write findings."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, OFFICERS, require

router = APIRouter()


class FindingActionIn(BaseModel):
    action: str = Field(..., pattern="^(accept|dismiss|escalate)$")
    reason: str = Field(..., min_length=3)


@router.get("/applications/{app_id}/findings")
def list_findings(app_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id::text, application_id::text, source_code, tier, result, reason,
                   evidence, recheck_recipe, depends_on_fields, clause_ref, created_at
            FROM findings WHERE application_id = %s
            ORDER BY tier, created_at
            """,
            (str(app_id),),
        )
        findings = rows_as_dicts(cur)
        for f in findings:
            f.setdefault("clause_ref", "PLACEHOLDER")
            if f.get("result") == "UNKNOWN":
                f["never_rejects"] = True
        return {"findings": findings, "synthetic_data": True}


@router.post("/findings/{finding_id}/action")
def reviewer_action(finding_id: UUID, body: FindingActionIn, request: Request, user=require(*OFFICERS)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, application_id, result FROM findings WHERE id = %s", (str(finding_id),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")
        _fid, app_id, result = row
        if result == "UNKNOWN" and body.action == "accept":
            # UNKNOWN is never a rejection; accepting an UNKNOWN finding records a human note only.
            pass
        if body.action in ("accept", "dismiss"):
            cur.execute(
                """
                INSERT INTO reviewer_actions (finding_id, action, reason, user_id)
                VALUES (%s, %s, %s, %s)
                """,
                (str(finding_id), body.action, body.reason, user.sub),
            )
        else:
            cur.execute(
                """
                INSERT INTO information_requests
                    (application_id, requested_by, document_or_field, reason, due_at, state)
                VALUES (%s, %s, %s, %s, NOW() + INTERVAL '7 days', 'OPEN')
                """,
                (str(app_id), user.sub, f"finding:{finding_id}", body.reason),
            )
        audit(
            conn,
            user.username,
            "reviewer_action",
            {
                "finding_id": str(finding_id),
                "action": body.action,
                "reason": body.reason,
                "synthetic_data": True,
            },
        )
        return {"ok": True, "action": body.action, "synthetic_data": True}
