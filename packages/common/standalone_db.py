"""Standalone SQLite-backed DB engine for demo and zero-dependency deployments (Render free tier).
Provides a psycopg2-compatible connection and thread pool adapter.
Automatically initializes full schema and seeds synthetic demo data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from packages.common.paths import DATA_DIR

log = logging.getLogger("aicte.standalone_db")

STANDALONE_DB_PATH = DATA_DIR / "aicte_standalone.db"


def _dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))


def _gen_uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _translate_sql(sql: str) -> str:
    """Translate PostgreSQL dialect SQL to SQLite compatible SQL."""
    # Remove Postgres type casts: ::text, ::jsonb, ::date, ::uuid, ::bytea, ::int, etc.
    s = re.sub(r"::[a-zA-Z0-9_]+", "", sql)
    # Convert %s placeholder to ? for SQLite parameter binding
    s = re.sub(r"(?<!%)%s", "?", s)
    # Unescape %%
    s = s.replace("%%", "%")
    # Replace boolean literals if unquoted
    s = re.sub(r"\btrue\b", "1", s, flags=re.IGNORECASE)
    s = re.sub(r"\bfalse\b", "0", s, flags=re.IGNORECASE)
    return s


class StandaloneCursor:
    """Wraps an sqlite3.Cursor to provide psycopg2-compatible interface."""

    def __init__(self, raw_cursor: sqlite3.Cursor, conn: StandaloneConnection):
        self._cur = raw_cursor
        self._conn = conn

    def execute(self, query: str, params: Optional[Any] = None):
        t_sql = _translate_sql(query)
        if params is None:
            return self._cur.execute(t_sql)
        if isinstance(params, (list, tuple)):
            # convert any UUID objects or dict/json to string/json string
            clean_params = []
            for p in params:
                if isinstance(p, uuid.UUID):
                    clean_params.append(str(p))
                elif isinstance(p, dict) or isinstance(p, list):
                    clean_params.append(json.dumps(p))
                elif isinstance(p, datetime):
                    clean_params.append(p.isoformat())
                else:
                    clean_params.append(p)
            return self._cur.execute(t_sql, clean_params)
        elif isinstance(params, dict):
            clean_dict = {
                k: str(v) if isinstance(v, uuid.UUID) else json.dumps(v) if isinstance(v, (dict, list)) else v
                for k, v in params.items()
            }
            return self._cur.execute(t_sql, clean_dict)
        return self._cur.execute(t_sql, params)

    def executemany(self, query: str, seq_of_parameters):
        t_sql = _translate_sql(query)
        return self._cur.executemany(t_sql, seq_of_parameters)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size else self._cur.fetchmany()

    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class StandaloneConnection:
    """Wraps an sqlite3 connection with psycopg2-like autocommit/commit/rollback semantics."""

    def __init__(self, raw_conn: sqlite3.Connection):
        self._conn = raw_conn
        self.autocommit = False

    def cursor(self):
        return StandaloneCursor(self._conn.cursor(), self)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


class StandalonePool:
    """Psycopg2 ThreadedConnectionPool-compatible pool backed by SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()

    def _create_conn(self) -> StandaloneConnection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        # Register PostgreSQL compatibility functions
        raw.create_function("gen_random_uuid", 0, _gen_uuid)
        raw.create_function("now", 0, _now_iso)
        raw.create_function("set_config", 3, lambda name, val, is_local: val)
        raw.create_function("set_config", 2, lambda name, val: val)

        def _audit_append(actor: str, action: str, payload_raw: str) -> int:
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except Exception:
                payload = {"data": str(payload_raw)}
            cur = raw.cursor()
            cur.execute("SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1")
            row = cur.fetchone()
            prev_hash = row[1] if row else ""
            cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM audit_log")
            next_seq = cur.fetchone()[0]
            ts = _now_iso()
            record_str = f"{next_seq}:{ts}:{actor}:{action}:{json.dumps(payload, sort_keys=True)}:{prev_hash}"
            record_hash = hashlib.sha256(record_str.encode()).hexdigest()
            cur.execute(
                "INSERT INTO audit_log (seq, ts, actor, action, payload, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_seq, ts, actor, action, json.dumps(payload), prev_hash, record_hash),
            )
            raw.commit()
            return next_seq

        raw.create_function("audit_append", 3, _audit_append)
        return StandaloneConnection(raw)

    def getconn(self) -> StandaloneConnection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_conn()
        return self._local.conn

    def putconn(self, conn: StandaloneConnection):
        # In SQLite thread-local model, keep open for thread reuse
        pass

    def closeall(self):
        with self._lock:
            if hasattr(self._local, "conn") and self._local.conn:
                try:
                    self._local.conn.close()
                except Exception:
                    pass
                self._local.conn = None


def init_standalone_db(db_path: Path = STANDALONE_DB_PATH) -> StandalonePool:
    """Ensure schema and seed synthetic data exist in standalone DB."""
    pool = StandalonePool(db_path)
    conn = pool.getconn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS institutions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        address TEXT,
        city TEXT,
        state TEXT,
        pin_code TEXT,
        is_canary INT DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        institution_id TEXT,
        is_active INT DEFAULT 1,
        failed_login_count INT DEFAULT 0,
        locked_until TEXT,
        last_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        institution_id TEXT NOT NULL,
        declared_category TEXT NOT NULL,
        academic_year TEXT NOT NULL,
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        stage TEXT NOT NULL DEFAULT 'SUBMITTED',
        ruleset_id TEXT,
        ruleset_hash TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        type_declared TEXT,
        type_detected TEXT,
        file_ref TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        page_count INT,
        key_id TEXT,
        original_filename TEXT,
        file_size_bytes INT,
        version INT DEFAULT 1,
        previous_version_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS extracted_fields (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        field TEXT NOT NULL,
        value TEXT,
        normalized TEXT,
        page INT,
        bbox TEXT,
        confidence REAL,
        extractor TEXT,
        agree INT,
        variant_readings TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS findings (
        id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        source_code TEXT NOT NULL,
        tier INT NOT NULL,
        result TEXT NOT NULL,
        reason TEXT,
        evidence TEXT,
        recheck_recipe TEXT,
        depends_on_fields TEXT,
        clause_ref TEXT DEFAULT 'PLACEHOLDER',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS document_status (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        status TEXT NOT NULL,
        source TEXT,
        result_hash TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_scores (
        id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        score REAL NOT NULL,
        features TEXT,
        model_version TEXT,
        threshold_used REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS review_items (
        id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        level INT NOT NULL,
        reason TEXT,
        assignee TEXT,
        state TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviewer_actions (
        id TEXT PRIMARY KEY,
        finding_id TEXT NOT NULL,
        action TEXT NOT NULL,
        reason TEXT NOT NULL,
        user_id TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        application_id TEXT,
        message TEXT,
        severity TEXT DEFAULT 'medium',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        delivered_at TEXT,
        acknowledged_by TEXT,
        acknowledged_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS consent_artifacts (
        id TEXT PRIMARY KEY,
        institution_id TEXT NOT NULL,
        granted_by TEXT NOT NULL,
        document_types TEXT NOT NULL,
        purpose TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS system_mode (
        id INT PRIMARY KEY,
        mode TEXT NOT NULL DEFAULT 'NORMAL',
        since TEXT DEFAULT CURRENT_TIMESTAMP,
        reason TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rule_sets (
        id TEXT PRIMARY KEY,
        version INT NOT NULL,
        effective_from TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        content_hash TEXT,
        author TEXT NOT NULL,
        approver TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id TEXT PRIMARY KEY,
        ruleset_id TEXT NOT NULL,
        code TEXT NOT NULL,
        title TEXT NOT NULL,
        clause_ref TEXT NOT NULL DEFAULT '<PLACEHOLDER: fill from handbook>',
        tier INT NOT NULL,
        severity TEXT DEFAULT 'medium',
        rectifiable INT DEFAULT 0,
        clears_with TEXT,
        categories TEXT,
        definition TEXT NOT NULL,
        depends_on_fields TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        payload TEXT NOT NULL,
        prev_hash TEXT NOT NULL DEFAULT '',
        hash TEXT NOT NULL
    )
    """)

    cur.execute("INSERT OR IGNORE INTO system_mode (id, mode) VALUES (1, 'NORMAL')")
    conn.commit()

    # Seed data if users table is empty
    cur.execute("SELECT count(*) FROM users")
    user_count = cur.fetchone()[0]
    if user_count == 0:
        log.info("Seeding synthetic data into Standalone SQLite database...")
        _seed_standalone(cur, conn)

    return pool


def _seed_standalone(cur: StandaloneCursor, conn: StandaloneConnection):
    from services.api.app.auth.routes import hash_password

    pw_hash = hash_password("demo123")

    institutions = [
        ("11111111-1111-1111-1111-111111111111", "Sunrise Technical Institute", "SUNRISE-001", "123 Academic Road", "Bengaluru", "Karnataka", "560001"),
        ("22222222-2222-2222-2222-222222222222", "Horizon Engineering College", "HORIZON-001", "456 University Ave", "Chennai", "Tamil Nadu", "600001"),
        ("33333333-3333-3333-3333-333333333333", "Pinnacle College of Science", "PINNACLE-001", "789 Knowledge Park", "Hyderabad", "Telangana", "500001"),
        ("44444444-4444-4444-4444-444444444444", "Greenfield Institute of Technology", "GIT-001", "101 Metro Way", "Pune", "Maharashtra", "411001"),
        ("55555555-5555-5555-5555-555555555555", "Westland Engineering College", "WEC-001", "202 Ring Road", "Ahmedabad", "Gujarat", "380001"),
        ("66666666-6666-6666-6666-666666666666", "Rajendra Institute of Management", "RIM-001", "303 Palace Road", "Jaipur", "Rajasthan", "302001"),
        ("77777777-7777-7777-7777-777777777777", "Northstar Academy of Sciences", "NAS-001", "404 Salt Lake", "Kolkata", "West Bengal", "700001"),
        ("88888888-8888-8888-8888-888888888888", "Eastern Polytechnic Institute", "EPI-001", "505 Infocity", "Bhubaneswar", "Odisha", "751001"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO institutions (id, name, code, address, city, state, pin_code) VALUES (?, ?, ?, ?, ?, ?, ?)",
        institutions,
    )

    users = [
        ("aaaa0001-0001-0001-0001-000000000001", "sunrise_admin", "admin@sunrise.edu", pw_hash, "institution_user", "11111111-1111-1111-1111-111111111111"),
        ("aaaa0002-0002-0002-0002-000000000002", "officer_raj", "raj@aicte.gov", pw_hash, "scrutiny_officer", None),
        ("aaaa0003-0003-0003-0003-000000000003", "supervisor_priya", "priya@aicte.gov", pw_hash, "supervisor", None),
        ("aaaa0004-0004-0004-0004-000000000004", "auditor_amit", "amit@aicte.gov", pw_hash, "auditor", None),
        ("aaaa0005-0005-0005-0005-000000000005", "rules_meera", "meera@aicte.gov", pw_hash, "rules_admin", None),
        ("aaaa0006-0006-0006-0006-000000000006", "sysadmin_dev", "dev@aicte.gov", pw_hash, "sysadmin", None),
        ("aaaa0007-0007-0007-0007-000000000007", "horizon_admin", "admin@horizon.edu", pw_hash, "institution_user", "22222222-2222-2222-2222-222222222222"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO users (id, username, email, pw_hash, role, institution_id) VALUES (?, ?, ?, ?, ?, ?)",
        users,
    )

    apps = [
        ("bbbb0001-0001-0001-0001-000000000001", "11111111-1111-1111-1111-111111111111", "EOA Renewal", "2025-26", "UNDER_REVIEW"),
        ("bbbb0002-0002-0002-0002-000000000002", "22222222-2222-2222-2222-222222222222", "New Approval", "2025-26", "SUBMITTED"),
        ("bbbb0003-0003-0003-0003-000000000003", "33333333-3333-3333-3333-333333333333", "EOA Renewal", "2025-26", "DECISION_PENDING"),
        ("bbbb0004-0004-0004-0004-000000000004", "44444444-4444-4444-4444-444444444444", "Intake Enhancement", "2025-26", "APPROVED"),
        ("bbbb0005-0005-0005-0005-000000000005", "55555555-5555-5555-5555-555555555555", "EOA Renewal", "2025-26", "REJECTED"),
        ("bbbb0006-0006-0006-0006-000000000006", "66666666-6666-6666-6666-666666666666", "New Approval", "2025-26", "EXTRACTING"),
        ("bbbb0007-0007-0007-0007-000000000007", "77777777-7777-7777-7777-777777777777", "EOA Renewal", "2025-26", "UNDER_REVIEW"),
        ("bbbb0008-0008-0008-0008-000000000008", "88888888-8888-8888-8888-888888888888", "Intake Enhancement", "2025-26", "INGESTING"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO applications (id, institution_id, declared_category, academic_year, stage) VALUES (?, ?, ?, ?, ?)",
        apps,
    )

    risk_scores = [
        ("bbbb0001-0001-0001-0001-000000000001", 0.73, "seed-static"),
        ("bbbb0002-0002-0002-0002-000000000002", 0.21, "seed-static"),
        ("bbbb0003-0003-0003-0003-000000000003", 0.88, "seed-static"),
        ("bbbb0004-0004-0004-0004-000000000004", 0.12, "seed-static"),
        ("bbbb0005-0005-0005-0005-000000000005", 0.95, "seed-static"),
        ("bbbb0006-0006-0006-0006-000000000006", 0.45, "seed-static"),
        ("bbbb0007-0007-0007-0007-000000000007", 0.62, "seed-static"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO risk_scores (id, application_id, score, model_version) VALUES (?, ?, ?, ?)",
        [(_gen_uuid(), app_id, score, mv) for app_id, score, mv in risk_scores],
    )

    docs = [
        ("cccc0001-0001-0001-0001-000000000001", "bbbb0001-0001-0001-0001-000000000001", "Trust Deed", "sunrise/trust_deed.pdf", "a1b2c3d4e5f6", 3),
        ("cccc0002-0002-0002-0002-000000000002", "bbbb0001-0001-0001-0001-000000000001", "Affidavit", "sunrise/affidavit.pdf", "b2c3d4e5f6a1", 2),
        ("cccc0003-0003-0003-0003-000000000003", "bbbb0001-0001-0001-0001-000000000001", "Stamp Paper", "sunrise/stamp_paper.pdf", "c3d4e5f6a1b2", 1),
        ("cccc0004-0004-0004-0004-000000000004", "bbbb0001-0001-0001-0001-000000000001", "Faculty List", "sunrise/faculty_list.pdf", "d4e5f6a1b2c3", 5),
        ("cccc0005-0005-0005-0005-000000000005", "bbbb0001-0001-0001-0001-000000000001", "NOC Certificate", "sunrise/noc_certificate.pdf", "e5f6a1b2c3d4", 1),
        # Pinnacle (bbbb0003) docs
        ("cccc0031-0031-0031-0031-000000000031", "bbbb0003-0003-0003-0003-000000000003", "Trust Deed", "pinnacle/trust_deed.pdf", "p1p2p3p4p5p6", 4),
        ("cccc0032-0032-0032-0032-000000000032", "bbbb0003-0003-0003-0003-000000000003", "Land Certificate", "pinnacle/land_deed.pdf", "l1l2l3l4l5l6", 6),
        ("cccc0033-0033-0033-0033-000000000033", "bbbb0003-0003-0003-0003-000000000003", "Fire Safety", "pinnacle/fire_safety.pdf", "f1f2f3f4f5f6", 2),
        ("cccc0034-0034-0034-0034-000000000034", "bbbb0003-0003-0003-0003-000000000003", "Faculty Roster", "pinnacle/faculty_roster.pdf", "r1r2r3r4r5r6", 8),
        # Northstar (bbbb0007) docs
        ("cccc0071-0071-0071-0071-000000000071", "bbbb0007-0007-0007-0007-000000000007", "Trust Deed", "northstar/trust_deed.pdf", "n1n2n3n4n5n6", 3),
        ("cccc0072-0072-0072-0072-000000000072", "bbbb0007-0007-0007-0007-000000000007", "Affiliation Order", "northstar/affiliation.pdf", "a7a7a7a7a7a7", 2),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO documents (id, application_id, type_declared, file_ref, sha256, page_count) VALUES (?, ?, ?, ?, ?, ?)",
        docs,
    )

    doc_statuses = [
        ("cccc0001-0001-0001-0001-000000000001", "VERIFIED", "signature_check"),
        ("cccc0002-0002-0002-0002-000000000002", "VERIFIED", "signature_check"),
        ("cccc0003-0003-0003-0003-000000000003", "VERIFIED", "signature_check"),
        ("cccc0004-0004-0004-0004-000000000004", "MANUAL_REVIEW_REQUIRED", "extraction_disagreement"),
        ("cccc0005-0005-0005-0005-000000000005", "SOURCE_UNAVAILABLE", "issuer_503"),
        ("cccc0031-0031-0031-0031-000000000031", "VERIFIED", "signature_check"),
        ("cccc0032-0032-0032-0032-000000000032", "MISMATCH_DETECTED", "land_record_crosscheck"),
        ("cccc0033-0033-0033-0033-000000000033", "EXPIRED", "date_check"),
        ("cccc0034-0034-0034-0034-000000000034", "MANUAL_REVIEW_REQUIRED", "faculty_ratio"),
        ("cccc0071-0071-0071-0071-000000000071", "VERIFIED", "signature_check"),
        ("cccc0072-0072-0072-0072-000000000072", "VERIFIED", "university_portal"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO document_status (id, document_id, status, source) VALUES (?, ?, ?, ?)",
        [(_gen_uuid(), d_id, st, src) for d_id, st, src in doc_statuses],
    )

    fields = [
        ("cccc0001-0001-0001-0001-000000000001", "Institution Name", "Sunrise Technical Institute", "sunrise technical institute", 1, 0.98, "pdfplumber", 1),
        ("cccc0001-0001-0001-0001-000000000001", "Trust Name", "Sunrise Education Trust", "sunrise education trust", 1, 0.96, "pdfplumber", 1),
        ("cccc0001-0001-0001-0001-000000000001", "PAN Number", "AAACT1234A", "aaact1234a", 1, 0.90, "pdfplumber", 1),
        ("cccc0002-0002-0002-0002-000000000002", "Affidavit Date", "2025-01-15", "2025-01-15", 1, 0.95, "pdfplumber", 1),
        ("cccc0002-0002-0002-0002-000000000002", "Signatory Name", "Dr. R. Kumar", "dr r kumar", 1, 0.93, "pdfplumber", 1),
        ("cccc0003-0003-0003-0003-000000000003", "Stamp Paper Date", "2025-02-01", "2025-02-01", 1, 0.97, "pdfplumber", 1),
        ("cccc0003-0003-0003-0003-000000000003", "Stamp Paper Value", "₹500", "500", 1, 0.99, "pdfplumber", 1),
        ("cccc0004-0004-0004-0004-000000000004", "Faculty Count", "42", "42", 1, 0.91, "pdfplumber", 1),
        ("cccc0005-0005-0005-0005-000000000005", "NOC Issuer", "State Govt of Karnataka", "state govt of karnataka", 1, 0.94, "pdfplumber", 1),
        # Pinnacle fields
        ("cccc0032-0032-0032-0032-000000000032", "Land Area (Acres)", "3.8", "3.8", 1, 0.89, "pdfplumber", 1),
        ("cccc0032-0032-0032-0032-000000000032", "Survey Number", "142/3B", "142/3b", 1, 0.94, "pdfplumber", 1),
        ("cccc0033-0033-0033-0033-000000000033", "Certificate Validity", "2024-12-31", "2024-12-31", 1, 0.97, "pdfplumber", 1),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO extracted_fields (id, document_id, field, value, normalized, page, confidence, extractor, agree) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(_gen_uuid(), d_id, f, val, norm, pg, conf, ext, agr) for d_id, f, val, norm, pg, conf, ext, agr in fields],
    )

    findings = [
        ("dddd0001-0001-0001-0001-000000000001", "bbbb0001-0001-0001-0001-000000000001", "D04-date-inconsistency", 1, "FALSE",
         "Affidavit date (2025-01-15) conflicts with stamp paper date (2025-02-01). Stamp purchased after affidavit executed.",
         json.dumps({"documents": ["cccc0002-0002-0002-0002-000000000002", "cccc0003-0003-0003-0003-000000000003"], "fields": ["affidavit_date", "stamp_paper_date"], "bounding_boxes": [{"doc_id": "cccc0002-0002-0002-0002-000000000002", "page": 1, "x": 120, "y": 340, "w": 200, "h": 25}, {"doc_id": "cccc0003-0003-0003-0003-000000000003", "page": 1, "x": 80, "y": 150, "w": 180, "h": 20}]}),
         "Compare affidavit date with stamp paper date. Verify stamp paper was purchased before affidavit execution."),
        ("dddd0002-0002-0002-0002-000000000002", "bbbb0001-0001-0001-0001-000000000001", "D13-source-unavailable", 2, "UNKNOWN",
         "NOC issuer verification endpoint returned 503. UNKNOWN is not FALSE.",
         json.dumps({"documents": ["cccc0005-0005-0005-0005-000000000005"], "status": "SOURCE_UNAVAILABLE"}),
         "Retry external issuer endpoint with exponential backoff."),
        # Pinnacle findings
        ("dddd0031-0031-0031-0031-000000000031", "bbbb0003-0003-0003-0003-000000000003", "D09-land-area-shortfall", 2, "FALSE",
         "Declared land area is 5.0 acres, but verified municipal land registry indicates only 3.8 acres. Deficit of 1.2 acres.",
         json.dumps({"documents": ["cccc0032-0032-0032-0032-000000000032"], "fields": ["land_area"]}),
         "Request certified survey map from District Revenue Officer."),
        ("dddd0032-0032-0032-0032-000000000032", "bbbb0003-0003-0003-0003-000000000003", "D02-expired-certificate", 1, "FALSE",
         "Fire & Safety certificate expired on 2024-12-31 prior to application submission.",
         json.dumps({"documents": ["cccc0033-0033-0033-0033-000000000033"], "fields": ["expiry_date"]}),
         "Upload valid renewed Fire & Safety NOC from Fire Department."),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO findings (id, application_id, source_code, tier, result, reason, evidence, recheck_recipe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        findings,
    )

    review_items = [
        ("eeee0001-0001-0001-0001-000000000001", "bbbb0001-0001-0001-0001-000000000001", 2, "Sunrise D04+D13 review", "aaaa0002-0002-0002-0002-000000000002", "assigned"),
        ("eeee0002-0002-0002-0002-000000000002", "bbbb0003-0003-0003-0003-000000000003", 3, "Pinnacle D09 Land Deficit & D02 Expired Cert", None, "pending"),
        ("eeee0003-0003-0003-0003-000000000003", "bbbb0007-0007-0007-0007-000000000007", 2, "Northstar Tier 2 Verification", "aaaa0003-0003-0003-0003-000000000003", "assigned"),
        ("eeee0004-0004-0004-0004-000000000004", "bbbb0006-0006-0006-0006-000000000006", 1, "Rajendra Incomplete Extraction", None, "pending"),
        ("eeee0005-0005-0005-0005-000000000005", "bbbb0002-0002-0002-0002-000000000002", 0, "Horizon Automated Level 0 Clearance", None, "pending"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO review_items (id, application_id, level, reason, assignee, state) VALUES (?, ?, ?, ?, ?, ?)",
        review_items,
    )

    alerts = [
        ("al0001", "FINDING_RAISED", "bbbb0001-0001-0001-0001-000000000001", "D04 date inconsistency on Sunrise affidavit vs stamp paper", "high"),
        ("al0002", "SOURCE_OUTAGE", "bbbb0001-0001-0001-0001-000000000001", "NOC issuer 503 — verification debt increased. UNKNOWN is not FALSE.", "medium"),
        ("al0003", "FINDING_RAISED", "bbbb0003-0003-0003-0003-000000000003", "D09 land deficit: 3.8 acres verified vs 5.0 acres required", "high"),
        ("al0004", "EXTRACTION_UNCERTAIN", "bbbb0006-0006-0006-0006-000000000006", "Rajendra Institute extraction confidence below 0.65; routed to queue", "low"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO alerts (id, type, application_id, message, severity) VALUES (?, ?, ?, ?, ?)",
        alerts,
    )

    conn.commit()
    log.info("Synthetic data seeded successfully in Standalone SQLite database.")
