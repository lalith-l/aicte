"""Project paths and DB connection settings in one place (no hard-coded user paths)."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRETS_DIR = PROJECT_ROOT / "secrets"
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = DATA_DIR / "storage"
MAIL_DIR = DATA_DIR / "mail"
SYNTH_DIR = DATA_DIR / "synth"
PDF_DIR = SYNTH_DIR / "pdfs"
CERT_DIR = SYNTH_DIR / "certs"
RULES_DIR = PROJECT_ROOT / "rules"
REPORT_DIR = PROJECT_ROOT / "eval" / "reports"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

DB_NAME = os.environ.get("AICTE_DB_NAME", "aicte_validator")
PG_HOST = os.environ.get("PG_HOST", "/tmp")
PG_BIN = os.environ.get("PG_BIN", "/opt/homebrew/opt/postgresql@16/bin")

ISSUERS_URL = os.environ.get("AICTE_ISSUERS_URL", "http://127.0.0.1:8002")
PORTAL_URL = os.environ.get("AICTE_PORTAL_URL", "http://127.0.0.1:8001")
API_URL = os.environ.get("AICTE_API_URL", "http://127.0.0.1:8000")


def ensure_dirs() -> None:
    for p in (STORAGE_DIR, MAIL_DIR, PDF_DIR, CERT_DIR, REPORT_DIR, SNAPSHOT_DIR):
        p.mkdir(parents=True, exist_ok=True)
    try:
        SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
    except OSError:
        pass


def role_connect_kwargs(role: str) -> dict:
    return dict(dbname=DB_NAME, user=role, password=f"{role}_dev", host=PG_HOST)
