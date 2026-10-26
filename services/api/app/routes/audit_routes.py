"""Audit log listing, chain verifier, published head hashes."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from packages.audit.chain import full_report, list_published_heads, publish_head, verify_chain_db
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import require

router = APIRouter()


@router.get("")
@router.get("/")
def list_log(request: Request, limit: int = Query(100, le=500), user=require("auditor", "sysadmin")):
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT seq, ts AS created_at, actor, action, payload AS data, prev_hash, hash "
            "FROM audit_log ORDER BY seq DESC LIMIT %s",
            (limit,),
        )
        return {"entries": rows_as_dicts(cur), "synthetic_data": True}


@router.get("/verify")
def verify(request: Request, user=require("auditor", "sysadmin")):
    with db(request, user) as conn:
        report = full_report(conn)
        audit(conn, user.username, "audit_chain_verified", {"all_ok": report["all_ok"], "synthetic_data": True})
        return {**report, "synthetic_data": True}


@router.get("/heads")
def heads(user=require("auditor", "sysadmin")):
    return {"heads": list_published_heads(), "synthetic_data": True}


@router.post("/publish-head")
def publish(request: Request, user=require("auditor", "sysadmin")):
    with db(request, user) as conn:
        path = publish_head(conn)
        st = verify_chain_db(conn)
        audit(
            conn,
            user.username,
            "head_hash_published",
            {"path": str(path), "head_seq": st.head_seq, "synthetic_data": True},
        )
        return {"path": str(path), "head_seq": st.head_seq, "head_hash": st.head_hash, "synthetic_data": True}
