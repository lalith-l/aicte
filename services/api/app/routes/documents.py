"""Documents + extracted fields. Ingestion uses the sandbox-safe gate."""
from __future__ import annotations

from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from packages.common.paths import STORAGE_DIR
from packages.common.validators import mask_identifier
from packages.ingest.gate import IngestionError, ingest_document
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, OFFICERS, STAFF, require

router = APIRouter()

SENSITIVE_FIELDS = ("pan", "gstin", "aadhaar")


def _mask_fields(fields: list[dict], role: str) -> list[dict]:
    out = []
    for f in fields:
        item = dict(f)
        name = (item.get("field") or "").lower()
        if any(s in name for s in SENSITIVE_FIELDS) and role == "institution_user":
            item["value"] = mask_identifier(item.get("value"))
            item["normalized"] = mask_identifier(item.get("normalized"))
        conf = item.get("confidence")
        agree = item.get("agree")
        if item.get("result") is None:
            if agree is False:
                item["result"] = "UNKNOWN"
            elif conf is not None and conf < 0.5:
                item["result"] = "UNKNOWN"
            else:
                item["result"] = "TRUE"
        out.append(item)
    return out


@router.get("/applications/{app_id}/documents")
def list_documents(app_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.id::text, d.application_id::text, d.type_declared, d.type_detected,
                   d.file_ref, d.sha256, d.page_count, d.created_at,
                   (SELECT ds.status FROM document_status ds
                      WHERE ds.document_id = d.id ORDER BY ds.created_at DESC LIMIT 1) AS status
            FROM documents d
            WHERE d.application_id = %s
            ORDER BY d.created_at
            """,
            (str(app_id),),
        )
        docs = rows_as_dicts(cur)
        for doc in docs:
            cur.execute(
                """
                SELECT field, value, normalized, page, bbox, confidence, extractor, agree
                FROM extracted_fields WHERE document_id = %s ORDER BY created_at
                """,
                (doc["id"],),
            )
            doc["extracted_fields"] = _mask_fields(rows_as_dicts(cur), user.role)
        return {"documents": docs, "synthetic_data": True}


@router.get("/documents/{doc_id}")
def get_document(doc_id: UUID, request: Request, user=require(*ALL_ROLES)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.id::text, d.application_id::text, d.type_declared, d.type_detected,
                   d.file_ref, d.sha256, d.page_count,
                   (SELECT ds.status FROM document_status ds
                      WHERE ds.document_id = d.id ORDER BY ds.created_at DESC LIMIT 1) AS status
            FROM documents d WHERE d.id = %s
            """,
            (str(doc_id),),
        )
        rows = rows_as_dicts(cur)
        if not rows:
            raise HTTPException(status_code=404, detail="Document not found")
        doc = rows[0]
        cur.execute(
            "SELECT field, value, normalized, page, bbox, confidence, extractor, agree "
            "FROM extracted_fields WHERE document_id = %s",
            (str(doc_id),),
        )
        doc["extracted_fields"] = _mask_fields(rows_as_dicts(cur), user.role)
        doc["synthetic_data"] = True
        return doc


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: UUID, request: Request, user=require(*ALL_ROLES)):
    """Serve stored PDF bytes (synthetic). Token query is accepted for <a href>."""
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute("SELECT file_ref FROM documents WHERE id = %s", (str(doc_id),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        ref = row[0]
    if not ref:
        raise HTTPException(status_code=404, detail="No file stored")
    path = Path(ref)
    if not path.is_absolute():
        path = STORAGE_DIR / ref
    if path.exists() and path.suffix.lower() == ".pdf":
        return FileResponse(path, media_type="application/pdf", filename=path.name)
    from packages.synth.templates import html_for, render_pdf
    import tempfile

    dest = Path(tempfile.gettempdir()) / f"{doc_id}.pdf"
    render_pdf(html_for("synthetic", {"document_id": str(doc_id), "synthetic": True}), dest)
    return FileResponse(dest, media_type="application/pdf", filename=f"{doc_id}.pdf")


@router.post("/applications/{app_id}/documents")
async def upload_document(
    app_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    type_declared: str = Form("other"),
    user=require(*OFFICERS, "institution_user"),
):
    data = await file.read()
    try:
        with db(request, user, role="app_det") as conn:
            result = ingest_document(
                data,
                application_id=str(app_id),
                declared_type=type_declared,
                actor_id=user.sub,
                conn=conn,
            )
            audit(
                conn,
                user.username,
                "document_ingested",
                {
                    "application_id": str(app_id),
                    "document_id": result["document_id"],
                    "sha256": result["sha256"],
                    "status": result["status"],
                    "synthetic_data": True,
                },
            )
            return {**result, "storage_root": str(STORAGE_DIR)}
    except IngestionError as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": e.message})


@router.get("/applications/{app_id}/diagnosis")
def diagnosis(app_id: UUID, request: Request, user=require(*STAFF, "institution_user")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT note_text FROM reviewer_notes
            WHERE application_id = %s AND note_text LIKE '%%seeded_diagnosis%%'
            ORDER BY created_at DESC LIMIT 1
            """,
            (str(app_id),),
        )
        row = cur.fetchone()
        if row:
            import json

            try:
                payload = json.loads(row[0])
            except json.JSONDecodeError:
                payload = {"recommendation": row[0], "label": "seeded static diagnosis, not computed"}
            payload["synthetic_data"] = True
            return payload
        return {
            "label": "seeded static diagnosis, not computed",
            "recommendation": "No diagnosis recorded.",
            "synthetic_data": True,
        }
