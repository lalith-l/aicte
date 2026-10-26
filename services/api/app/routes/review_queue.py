"""Review queue by level (0-3) with assignment."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import OFFICERS, require

router = APIRouter()


class AssignIn(BaseModel):
    assignee: str = "me"


@router.get("")
@router.get("/")
def list_queue(request: Request, level: int | None = Query(None), user=require(*OFFICERS, "auditor")):
    with db(request, user) as conn:
        cur = conn.cursor()
        sql = """
            SELECT ri.id::text, ri.application_id::text, ri.level,
                   upper(ri.state) AS status, ri.assignee::text AS assigned_to,
                   u.username AS assigned_to_username, ri.created_at, ri.reason,
                   i.name AS institution_name, i.code AS institution_code,
                   a.declared_category AS category,
                   (SELECT count(*) FROM findings f WHERE f.application_id = ri.application_id) AS findings_count
            FROM review_items ri
            JOIN applications a ON a.id = ri.application_id
            JOIN institutions i ON i.id = a.institution_id
            LEFT JOIN users u ON u.id = ri.assignee
        """
        params: list = []
        if level is not None:
            sql += " WHERE ri.level = %s"
            params.append(level)
        sql += " ORDER BY ri.created_at DESC"
        cur.execute(sql, params)
        return {"items": rows_as_dicts(cur), "synthetic_data": True}


@router.post("/{item_id}/assign")
def assign(item_id: UUID, body: AssignIn, request: Request, user=require(*OFFICERS)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE review_items SET assignee = %s, state = 'assigned' WHERE id = %s RETURNING application_id",
            (user.sub, str(item_id)),
        )
        row = cur.fetchone()
        if row:
            audit(
                conn,
                user.username,
                "review_assigned",
                {"item_id": str(item_id), "application_id": str(row[0]), "synthetic_data": True},
            )
        return {"ok": True, "assigned_to": user.username, "synthetic_data": True}
