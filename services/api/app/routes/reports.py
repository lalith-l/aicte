"""JSON + PDF reports. Hash is written to the audit chain."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Request

from packages.reports.generator import build_report, persist_json, persist_pdf
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, OFFICERS, require

router = APIRouter()


def _bundle(conn, app_id: str):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT d.id::text, d.type_declared, d.page_count,
               (SELECT ds.status FROM document_status ds
                  WHERE ds.document_id = d.id ORDER BY ds.created_at DESC LIMIT 1) AS status
        FROM documents d WHERE d.application_id = %s
        """,
        (app_id,),
    )
    docs = rows_as_dicts(cur)
    cur.execute(
        """
        SELECT id::text, source_code, tier, result, reason, recheck_recipe, clause_ref
        FROM findings WHERE application_id = %s
        """,
        (app_id,),
    )
    findings = rows_as_dicts(cur)
    return docs, findings


@router.get("/applications/{app_id}/report")
def get_report(app_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id::text, report_json, json_hash, created_at FROM reports "
            "WHERE application_id = %s ORDER BY created_at DESC LIMIT 1",
            (str(app_id),),
        )
        rows = rows_as_dicts(cur)
        if rows:
            return {"report": rows[0]["report_json"], "hash": rows[0]["json_hash"], "synthetic_data": True}
        docs, findings = _bundle(conn, str(app_id))
        report = build_report(str(app_id), docs, findings, str(uuid.uuid4()))
        return {"report": report.model_dump(), "synthetic_data": True}


@router.post("/applications/{app_id}/report")
def generate_report(app_id: UUID, request: Request, user=require(*OFFICERS)):
    report_id = str(uuid.uuid4())
    with db(request, user, role="app_det") as conn:
        docs, findings = _bundle(conn, str(app_id))
        report = build_report(str(app_id), docs, findings, report_id)
        path, digest = persist_json(report)
        pdf_ref = persist_pdf(report)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports (id, application_id, schema_version, report_json, json_hash, pdf_ref, generated_by)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
            """,
            (
                report_id,
                str(app_id),
                report.schema_version,
                report.model_dump_json(),
                digest,
                pdf_ref,
                user.username,
            ),
        )
        audit(
            conn,
            user.username,
            "report_generated",
            {"application_id": str(app_id), "report_id": report_id, "json_hash": digest, "synthetic_data": True},
        )
        return {"report": report.model_dump(), "hash": digest, "path": path, "synthetic_data": True}
