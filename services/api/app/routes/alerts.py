"""Alerts list + SSE stream."""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import OFFICERS, require

router = APIRouter()


@router.get("")
@router.get("/")
def list_alerts(request: Request, user=require(*OFFICERS, "auditor")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id::text, a.type, a.application_id::text, a.message, a.severity,
                   a.created_at, a.delivered_at, a.acknowledged_by::text, a.acknowledged_at,
                   i.name AS institution_name
            FROM alerts a
            LEFT JOIN applications app ON app.id = a.application_id
            LEFT JOIN institutions i ON i.id = COALESCE(a.institution_id, app.institution_id)
            ORDER BY a.created_at DESC
            LIMIT 200
            """
        )
        return {"alerts": rows_as_dicts(cur), "synthetic_data": True}


@router.post("/{alert_id}/ack")
def ack_alert(alert_id: UUID, request: Request, user=require(*OFFICERS)):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE alerts SET acknowledged_by = %s, acknowledged_at = NOW() WHERE id = %s",
            (user.sub, str(alert_id)),
        )
        audit(conn, user.username, "alert_acknowledged", {"alert_id": str(alert_id), "synthetic_data": True})
        return {"ok": True, "synthetic_data": True}


@router.get("/stream")
async def stream_alerts(request: Request, user=require(*OFFICERS, "auditor")):
    async def gen():
        last_seen = None
        while True:
            if await request.is_disconnected():
                break
            with db(request, user) as conn:
                cur = conn.cursor()
                if last_seen:
                    cur.execute(
                        "SELECT id::text, type, message, severity, created_at FROM alerts "
                        "WHERE created_at > %s ORDER BY created_at",
                        (last_seen,),
                    )
                else:
                    cur.execute(
                        "SELECT id::text, type, message, severity, created_at FROM alerts "
                        "ORDER BY created_at DESC LIMIT 5"
                    )
                rows = rows_as_dicts(cur)
            for row in rows:
                last_seen = row["created_at"]
                yield f"data: {json.dumps({**row, 'synthetic_data': True})}\n\n"
            yield "event: ping\ndata: {}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(gen(), media_type="text/event-stream")
