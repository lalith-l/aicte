"""Pipeline job queue endpoints (staff). Queue logic lives in packages.common.jobqueue."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from packages.common import jobqueue
from services.api.app.deps import db, rows_as_dicts
from services.api.app.rbac import OFFICERS, require

router = APIRouter()


class EnqueueIn(BaseModel):
    application_id: str
    stage: str = "INGEST"


@router.get("")
def list_jobs(request: Request, user=require(*OFFICERS, "auditor")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id::text, application_id::text, stage, status, error, created_at, completed_at "
            "FROM pipeline_jobs ORDER BY created_at DESC LIMIT 100"
        )
        return {"jobs": rows_as_dicts(cur), "synthetic_data": True}


@router.post("")
def enqueue_job(body: EnqueueIn, request: Request, user=require(*OFFICERS)):
    with db(request, user) as conn:
        jid = jobqueue.enqueue(conn, body.application_id, body.stage)
        return {"job_id": jid, "synthetic_data": True}


@router.get("/stats")
def stats(request: Request, user=require(*OFFICERS, "auditor")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, count(*) FROM pipeline_jobs GROUP BY 1")
        return {"counts": {r[0]: r[1] for r in cur.fetchall()}, "synthetic_data": True}
