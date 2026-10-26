"""Demo-only controls: chaos switch, role hint. Never enabled outside AICTE_DEMO_MODE."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from services.api.app.deps import audit, db
from services.api.app.rbac import ALL_ROLES, require

router = APIRouter()


class ChaosIn(BaseModel):
    enabled: bool


@router.get("/chaos")
def get_chaos(request: Request, user=require(*ALL_ROLES)):
    return {"enabled": bool(getattr(request.app.state, "chaos", False)), "synthetic_data": True}


@router.post("/chaos")
def set_chaos(body: ChaosIn, request: Request, user=require(*ALL_ROLES)):
    request.app.state.chaos = body.enabled
    try:
        import httpx
        from packages.common.paths import ISSUERS_URL, PORTAL_URL

        path = "/issuers/chaos/enable" if body.enabled else "/issuers/chaos/disable"
        httpx.post(f"{ISSUERS_URL}{path}", timeout=1.0)
        portal_path = "/portal/chaos/on" if body.enabled else "/portal/chaos/off"
        httpx.post(f"{PORTAL_URL}{portal_path}", timeout=1.0)
    except Exception:
        pass
    with db(request, user) as conn:
        audit(conn, user.username, "chaos_switch", {"enabled": body.enabled, "synthetic_data": True})
        cur = conn.cursor()
        if body.enabled:
            cur.execute(
                """
                INSERT INTO alerts (type, application_id, message, severity)
                VALUES ('SOURCE_OUTAGE', 'bbbb0001-0001-0001-0001-000000000001',
                        'Chaos switch: mock issuers returning 503. UNKNOWN is not FALSE.', 'high')
                """
            )
            cur.execute(
                """
                INSERT INTO document_status (document_id, status, source)
                VALUES ('cccc0005-0005-0005-0005-000000000005', 'SOURCE_UNAVAILABLE', 'chaos_switch')
                """
            )
    return {
        "enabled": body.enabled,
        "effect": "SOURCE_UNAVAILABLE — not a rejection",
        "synthetic_data": True,
    }
