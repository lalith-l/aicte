"""Shared request helpers: scoped DB access with RLS context, audit helpers."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator, Optional

from fastapi import Request

from services.api.app.auth.routes import TokenPayload


@contextmanager
def db(
    request: Request,
    user: Optional[TokenPayload] = None,
    role: str = "app_api",
    pipeline: bool = False,
) -> Iterator["psycopg2.extensions.connection"]:  # noqa: F821
    """Check out a pooled connection for DB role `role` and set RLS context.

    Context is set with set_config(..., is_local=true) so it dies with the transaction
    and can never leak to the next request that reuses the pooled connection.
    Commits on success, rolls back on error.
    """
    pool = request.app.state.pools[role]
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        if pipeline:
            cur.execute("SELECT set_config('app.role','pipeline',true)")
        elif user is not None:
            cur.execute("SELECT set_config('app.role',%s,true)", (user.role,))
            cur.execute("SELECT set_config('app.user_id',%s,true)", (user.sub,))
            cur.execute(
                "SELECT set_config('app.institution_id',%s,true)", (user.institution_id or "",)
            )
        cur.close()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def audit(conn, actor: str, action: str, payload: dict) -> int:
    """Append to the hash-chained audit log (SECURITY DEFINER function)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT audit_append(%s, %s, %s::jsonb)", (actor, action, json.dumps(payload, default=str))
    )
    seq = cur.fetchone()[0]
    cur.close()
    return seq


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "hex") and hasattr(value, "int"):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def rows_as_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [_jsonable(dict(zip(cols, r))) for r in cur.fetchall()]
