"""Applications list/detail — RLS enforced, PAN masked unless permissioned reveal."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from packages.common.validators import mask_identifier
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, OFFICERS, require

router = APIRouter()

LIST_SQL = """
SELECT a.id::text, a.institution_id::text, i.name AS institution_name, i.code AS institution_code,
       i.city, i.state, a.declared_category, a.academic_year, a.stage, a.created_at,
       (SELECT count(*) FROM findings f WHERE f.application_id = a.id) AS findings_count,
       (SELECT count(*) FROM findings f WHERE f.application_id = a.id AND f.result = 'UNKNOWN') AS unknowns_count,
       (SELECT count(*) FROM document_status ds
          JOIN documents d ON d.id = ds.document_id
          WHERE d.application_id = a.id AND ds.status = 'VERIFIED') AS verified_count,
       (SELECT count(*) FROM document_status ds
          JOIN documents d ON d.id = ds.document_id
          WHERE d.application_id = a.id) AS checked_docs_count,
       (SELECT score FROM risk_scores rs WHERE rs.application_id = a.id ORDER BY created_at DESC LIMIT 1) AS risk_score
FROM applications a
JOIN institutions i ON i.id = a.institution_id
ORDER BY a.created_at DESC
LIMIT 500
"""

DETAIL_SQL = """
SELECT a.id::text, a.institution_id::text, i.name AS institution_name, i.code AS institution_code,
       i.city, i.state, a.declared_category, a.academic_year, a.stage, a.created_at,
       (SELECT score FROM risk_scores rs WHERE rs.application_id = a.id ORDER BY created_at DESC LIMIT 1) AS risk_score
FROM applications a
JOIN institutions i ON i.id = a.institution_id
WHERE a.id = %s
"""


@router.get("")
@router.get("/")
def list_applications(request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(LIST_SQL)
        apps = rows_as_dicts(cur)
        return {"applications": apps, "synthetic_data": True}


@router.get("/{app_id}")
def get_application(app_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(DETAIL_SQL, (str(app_id),))
        rows = rows_as_dicts(cur)
        if not rows:
            raise HTTPException(status_code=404, detail="Application not found")
        row = rows[0]
        row["synthetic_data"] = True
        return row


@router.get("/{app_id}/pii")
def reveal_pii(
    app_id: UUID,
    request: Request,
    field: str = Query(..., description="Identifier field to reveal"),
    user=require(*OFFICERS, "auditor"),
):
    """Permissioned PAN/GSTIN reveal. Last-4 is shown by default; this logs a full reveal."""
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ef.field, ef.value FROM extracted_fields ef
            JOIN documents d ON d.id = ef.document_id
            WHERE d.application_id = %s AND lower(ef.field) LIKE %s
            LIMIT 20
            """,
            (str(app_id), f"%{field.lower()}%"),
        )
        rows = rows_as_dicts(cur)
        audit(
            conn,
            user.username,
            "pii_reveal",
            {"application_id": str(app_id), "field": field, "count": len(rows), "synthetic_data": True},
        )
        return {
            "application_id": str(app_id),
            "field": field,
            "values": [{"field": r["field"], "value": r["value"], "masked": mask_identifier(r["value"])} for r in rows],
            "synthetic_data": True,
        }
