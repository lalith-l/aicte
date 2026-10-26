"""System mode, chaos flag, crypto-shred, demo reset."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from packages.crypto.shred import shred_document
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import ALL_ROLES, require

router = APIRouter()


class ModeIn(BaseModel):
    mode: str
    reason: str = "demo"


class ShredIn(BaseModel):
    document_id: str


@router.get("/mode")
def get_mode(request: Request, user=require("auditor", "sysadmin", "scrutiny_officer", "supervisor", "rules_admin")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute("SELECT mode, since AS changed_at, reason FROM system_mode WHERE id = 1")
        rows = rows_as_dicts(cur)
        return {**(rows[0] if rows else {"mode": "NORMAL"}), "synthetic_data": True}


@router.put("/mode")
def set_mode(body: ModeIn, request: Request, user=require("sysadmin", "auditor")):
    if body.mode not in ("NORMAL", "DEGRADED"):
        from fastapi import HTTPException

        raise HTTPException(400, "mode must be NORMAL or DEGRADED")
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE system_mode SET mode = %s, since = NOW(), reason = %s WHERE id = 1",
            (body.mode, body.reason),
        )
        audit(conn, user.username, "system_mode_changed", {"mode": body.mode, "reason": body.reason})
        return {"mode": body.mode, "synthetic_data": True}


@router.post("/reset-demo")
def reset_demo(request: Request, user=require(*ALL_ROLES)):
    import subprocess
    import sys
    from packages.common.paths import PROJECT_ROOT

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "seed_demo.py")],
        capture_output=True,
        text=True,
    )
    with db(request, user) as conn:
        audit(conn, user.username, "demo_reset", {"returncode": result.returncode, "synthetic_data": True})
    return {"ok": result.returncode == 0, "log": result.stdout[-500:], "synthetic_data": True}


@router.post("/shred")
def shred(body: ShredIn, request: Request, user=require("sysadmin")):
    with db(request, user, role="app_det") as conn:
        ok = shred_document(conn, body.document_id)
        audit(conn, user.username, "crypto_shred", {"document_id": body.document_id, "ok": ok})
        return {"ok": ok, "synthetic_data": True}
