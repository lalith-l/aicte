"""Phase 0.4: auth — login, expiry, lockout on 6th bad attempt, rate limiting."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import timedelta

import psycopg2
import psycopg2.pool
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.common.paths import DB_NAME, PG_HOST  # noqa: E402
from services.api.app.auth import routes as auth  # noqa: E402

pytestmark = pytest.mark.gate


@pytest.fixture
def client(db_superuser):
    pool = psycopg2.pool.ThreadedConnectionPool(
        1, 3, dbname=DB_NAME, user="app_api", password="app_api_dev", host=PG_HOST
    )
    app = FastAPI()
    app.state.pools = {"app_api": pool}
    app.include_router(auth.router, prefix="/api/auth")

    from fastapi import Depends

    @app.get("/api/protected")
    def _p_get(u=Depends(auth.get_current_user)):
        return {"ok": True}

    @app.post("/api/protected")
    def _p_post(u=Depends(auth.get_current_user)):
        return {"ok": True}

    auth.reset_rate_limiter()

    username = f"authtest_{uuid.uuid4().hex[:8]}"
    cur = db_superuser.cursor()
    cur.execute(
        "INSERT INTO users (username, email, pw_hash, role) VALUES (%s,%s,%s,'auditor') RETURNING id",
        (username, f"{username}@example.test", auth.hash_password("correct-horse")),
    )
    uid = cur.fetchone()[0]
    db_superuser.commit()
    with TestClient(app) as c:
        c.username = username  # type: ignore[attr-defined]
        c.uid = str(uid)  # type: ignore[attr-defined]
        yield c
    db_superuser.rollback()
    cur = db_superuser.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    db_superuser.commit()
    pool.closeall()
    auth.reset_rate_limiter()


def _login(c, pw):
    return c.post("/api/auth/login", json={"username": c.username, "password": pw})


def test_login_and_me(client):
    r = _login(client, "correct-horse")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "auditor" and body["synthetic_data"] is True
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["username"] == client.username


def test_expired_token_rejected(client):
    tok = auth.create_token(
        client.uid, client.username, "auditor", expires_delta=timedelta(seconds=-5)
    )
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and "expired" in r.json()["detail"].lower()


def test_tampered_and_missing_token_rejected(client):
    tok = auth.create_token(client.uid, client.username, "auditor")
    bad = tok[:-3] + ("AAA" if not tok.endswith("AAA") else "BBB")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_sixth_bad_attempt_is_locked(client):
    for _ in range(5):
        assert _login(client, "wrong").status_code == 401
    # even the correct password is refused while locked
    assert _login(client, "correct-horse").status_code == 423


def test_failed_counter_resets_on_success(client):
    for _ in range(3):
        assert _login(client, "wrong").status_code == 401
    assert _login(client, "correct-horse").status_code == 200
    for _ in range(4):
        assert _login(client, "wrong").status_code == 401
    assert _login(client, "correct-horse").status_code == 200


def test_rate_limit(client):
    codes = [_login(client, "wrong").status_code for _ in range(auth.RATE_LIMIT_MAX + 3)]
    assert 429 in codes


def test_cookie_not_accepted_for_state_changing_requests(client):
    r = _login(client, "correct-horse")
    assert r.status_code == 200
    # cookie is set (HttpOnly, SameSite=Strict) ...
    assert "httponly" in r.headers["set-cookie"].lower()
    assert "samesite=strict" in r.headers["set-cookie"].lower()
    # cookie-only GET works (needed for SSE / <img>), cookie-only POST is rejected (CSRF)
    assert client.get("/api/protected").status_code == 200
    assert client.post("/api/protected").status_code == 401
    tok = r.json()["access_token"]
    assert (
        client.post("/api/protected", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    )
