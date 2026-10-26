"""FastAPI application: auth, health, CORS/CSP, RBAC-guarded routers.

All data is synthetic — every payload says so.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from contextlib import asynccontextmanager

import psycopg2.pool
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from packages.common.paths import DB_NAME, PG_HOST, ensure_dirs
from services.api.app.auth.routes import router as auth_router
from services.api.app.routes import (
    alerts,
    applications,
    audit_routes,
    demo,
    documents,
    findings,
    health,
    jobs,
    portal_routes,
    reports,
    review_queue,
    rules_routes,
    system_routes,
    verification,
)

log = logging.getLogger("aicte.main")

DEMO_MODE = os.environ.get("AICTE_DEMO_MODE", "1") == "1"
ROLES = ["app_api", "app_det", "app_model", "app_monitor", "app_readonly"]

# Render / production: single DATABASE_URL takes precedence over per-role local pools
_DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _parse_database_url(url: str) -> dict:
    """Parse postgres://user:pass@host:port/dbname into psycopg2 kwargs."""
    p = urlparse(url)
    kwargs = dict(
        dbname=p.path.lstrip("/"),
        user=p.username,
        password=p.password,
        host=p.hostname,
        port=p.port or 5432,
        sslmode="require",
    )
    return {k: v for k, v in kwargs.items() if v is not None}


def _create_pool(role: str, minconn: int = 1, maxconn: int = 5):
    if _DATABASE_URL:
        # Render / production: all roles share the single provided connection
        kwargs = _parse_database_url(_DATABASE_URL)
    else:
        # Local dev: connect with per-role PostgreSQL users
        kwargs = dict(
            dbname=DB_NAME,
            user=role,
            password=f"{role}_dev",
            host=PG_HOST,
        )
    return psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, **kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    try:
        app.state.pools = {r: _create_pool(r) for r in ROLES}
        log.info("DB connection pools initialised (%d roles)", len(ROLES))
    except Exception as exc:
        log.warning("DB pool creation failed: %s — running in limited/demo mode.", exc)
        app.state.pools = {}
    app.state.demo_mode = DEMO_MODE
    yield
    for pool in app.state.pools.values():
        try:
            pool.closeall()
        except Exception:
            pass


app = FastAPI(
    title="AICTE Validation Prototype",
    description="All data is synthetic. Prototype only.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — local dev origins + any *.onrender.com deploy
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
if _FRONTEND_URL:
    _ALLOWED_ORIGINS.append(_FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith(_DOC_PATHS):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Synthetic-Data"] = "true"
    return response


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(findings.router, prefix="/api", tags=["findings"])
app.include_router(verification.router, prefix="/api", tags=["verification"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(review_queue.router, prefix="/api/review-queue", tags=["review"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(audit_routes.router, prefix="/api/audit", tags=["audit"])
app.include_router(rules_routes.router, prefix="/api/rules", tags=["rules"])
app.include_router(system_routes.router, prefix="/api/system", tags=["system"])
app.include_router(portal_routes.router, prefix="/api/portal", tags=["institution-portal"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
if DEMO_MODE:
    app.include_router(demo.router, prefix="/api/demo", tags=["demo"])
    app.include_router(demo.router, prefix="/api/mock", tags=["demo"])
