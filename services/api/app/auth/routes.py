"""Authentication: PyJWT + argon2id, per-client rate limiting, account lockout.

- JWT secret comes from the environment or `secrets/jwt_secret` (auto-created, gitignored).
- Bearer header is required for every state-changing request.
- An HttpOnly SameSite=Strict cookie is also issued so GET-only consumers that cannot
  set headers (SSE `EventSource`, `<img>` page renders) can authenticate. Cookies are
  never accepted for POST/PUT/PATCH/DELETE (CSRF defence).

All data is synthetic.
"""

from __future__ import annotations

import os
import secrets as _secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer(auto_error=False)

_ph = None


def _get_ph():
    global _ph
    if _ph is None:
        from argon2 import PasswordHasher
        _ph = PasswordHasher()
    return _ph

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from packages.common.paths import SECRETS_DIR  # noqa: E402


def _load_jwt_secret() -> str:
    env = os.environ.get("JWT_SECRET")
    if env:
        return env
    path = SECRETS_DIR / "jwt_secret"
    SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
    if not path.exists():
        path.write_text(_secrets.token_urlsafe(48))
        path.chmod(0o600)
    return path.read_text().strip()


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
COOKIE_NAME = "aicte_session"

# --- rate limiter -----------------------------------------------------------
RATE_LIMIT_MAX = int(os.environ.get("LOGIN_RATE_LIMIT", "20"))
RATE_LIMIT_WINDOW_S = 60
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def reset_rate_limiter() -> None:
    with _hits_lock:
        _hits.clear()


def _rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _hits_lock:
        q = _hits[key]
        while q and now - q[0] > RATE_LIMIT_WINDOW_S:
            q.popleft()
        if len(q) >= RATE_LIMIT_MAX:
            return True
        q.append(now)
        return False


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_MINUTES * 60
    role: str
    username: str
    synthetic_data: bool = True


class TokenPayload(BaseModel):
    sub: str
    username: str
    role: str
    institution_id: Optional[str] = None
    exp: datetime


def hash_password(password: str) -> str:
    return _get_ph().hash(password)


def verify_password(password: str, pw_hash: str) -> bool:
    from argon2.exceptions import InvalidHashError, VerifyMismatchError
    try:
        return _get_ph().verify(pw_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_token(
    user_id: str,
    username: str,
    role: str,
    institution_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    import jwt
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "institution_id": institution_id,
        "exp": now
        + (expires_delta if expires_delta is not None else timedelta(minutes=JWT_EXPIRE_MINUTES)),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    import jwt
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> TokenPayload:
    if credentials is not None:
        return decode_token(credentials.credentials)
    if request.method in ("GET", "HEAD", "OPTIONS"):
        qtok = request.query_params.get("token")
        if qtok:
            return decode_token(qtok)
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie:
            return decode_token(cookie)
    raise HTTPException(status_code=401, detail="Not authenticated")


def _audit(cur, actor: str, action: str, payload: dict) -> None:
    import json

    cur.execute("SELECT audit_append(%s, %s, %s::jsonb)", (actor, action, json.dumps(payload)))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response):
    client = request.client.host if request.client else "unknown"
    if _rate_limited(f"{client}"):
        raise HTTPException(status_code=429, detail="Too many login attempts; slow down")

    pool = request.app.state.pools["app_api"]
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, pw_hash, role, institution_id, failed_login_count, locked_until "
            "FROM users WHERE username = %s AND is_active = true",
            (body.username,),
        )
        row = cur.fetchone()
        if not row:
            # Burn comparable time so username enumeration by timing is harder.
            verify_password(body.password, _get_ph().hash("x"))
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, pw_hash, role, inst_id, failed_count, locked_until = row

        if locked_until and locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail="Account locked")

        if not verify_password(body.password, pw_hash):
            new_count = failed_count + 1
            lock_until = None
            if new_count >= MAX_FAILED_LOGINS:
                lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            cur.execute(
                "UPDATE users SET failed_login_count = %s, locked_until = %s WHERE id = %s",
                (new_count, lock_until, user_id),
            )
            conn.commit()
            raise HTTPException(status_code=401, detail="Invalid credentials")

        cur.execute(
            "UPDATE users SET failed_login_count = 0, locked_until = NULL WHERE id = %s",
            (user_id,),
        )
        conn.commit()

        token = create_token(str(user_id), body.username, role, str(inst_id) if inst_id else None)
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="strict",
            secure=os.environ.get("AICTE_COOKIE_SECURE", "0") == "1",
            max_age=JWT_EXPIRE_MINUTES * 60,
            path="/",
        )
        return TokenResponse(access_token=token, role=role, username=body.username)
    finally:
        try:
            conn.rollback()
        finally:
            pool.putconn(conn)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def get_me(user: Annotated[TokenPayload, Depends(get_current_user)]):  # any authenticated role
    return {
        "user_id": user.sub,
        "username": user.username,
        "role": user.role,
        "institution_id": user.institution_id,
        "synthetic_data": True,
    }
