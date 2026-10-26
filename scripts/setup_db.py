"""Database setup: roles, tables, RLS policies, audit chain, and permission grants.

Run with: python scripts/setup_db.py
Requires: psql on PATH, database 'aicte_validator' already created.

This script creates the complete schema with:
- 6 database roles with least-privilege grants
- Append-only tables (findings, document_status, verification_results, indicators,
  risk_scores, reviewer_actions, audit_log) — no UPDATE or DELETE for any role
- State-update tables (applications, review_items, alerts, etc.) — normal UPDATE allowed
- DELETE allowed on file_keys for crypto-shredding
- FORCE ROW LEVEL SECURITY on data tables — applies even to table owner
- SECURITY DEFINER audit_append() function for hash-chain integrity
"""
from __future__ import annotations

import os
import subprocess
import sys

DB_NAME = os.environ.get("AICTE_DB_NAME", "aicte_validator")
PG_BIN = os.environ.get("PG_BIN", "/opt/homebrew/opt/postgresql@16/bin")

SCHEMA_SQL = r"""
-- ============================================================
-- 0. Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. Roles (idempotent with IF NOT EXISTS)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_api') THEN
        CREATE ROLE app_api LOGIN PASSWORD 'app_api_dev';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_det') THEN
        CREATE ROLE app_det LOGIN PASSWORD 'app_det_dev';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_model') THEN
        CREATE ROLE app_model LOGIN PASSWORD 'app_model_dev';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_monitor') THEN
        CREATE ROLE app_monitor LOGIN PASSWORD 'app_monitor_dev';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'migrator') THEN
        CREATE ROLE migrator LOGIN PASSWORD 'migrator_dev';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_readonly') THEN
        CREATE ROLE app_readonly LOGIN PASSWORD 'app_readonly_dev';
    END IF;
END
$$;

-- ============================================================
-- 2. Core Tables
-- ============================================================

-- Institutions and users
CREATE TABLE IF NOT EXISTS institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    pin_code TEXT,
    is_canary BOOLEAN DEFAULT FALSE,  -- only readable by app_monitor via sealed schema
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN (
        'institution_user', 'scrutiny_officer', 'supervisor',
        'auditor', 'rules_admin', 'sysadmin'
    )),
    institution_id UUID REFERENCES institutions(id),
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_count INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Applications
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id),
    declared_category TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    stage TEXT NOT NULL DEFAULT 'SUBMITTED',
    ruleset_id UUID,
    ruleset_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    type_declared TEXT,
    type_detected TEXT,
    file_ref TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    page_count INT,
    key_id UUID,
    original_filename TEXT,
    file_size_bytes BIGINT,
    version INT DEFAULT 1,
    previous_version_id UUID REFERENCES documents(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted fields
CREATE TABLE IF NOT EXISTS extracted_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    field TEXT NOT NULL,
    value TEXT,
    normalized TEXT,
    page INT,
    bbox JSONB,  -- {x, y, w, h}
    confidence REAL,
    extractor TEXT,  -- 'pdfplumber', 'pymupdf', 'paddleocr', 'tesseract'
    agree BOOLEAN,  -- both extractors agreed
    variant_readings JSONB,  -- stored when extractors disagree
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. Rules and Findings (APPEND-ONLY)
-- ============================================================

CREATE TABLE IF NOT EXISTS rule_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version INT NOT NULL,
    effective_from TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'effective', 'superseded')),
    content_hash TEXT,
    author TEXT NOT NULL,
    approver TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id UUID NOT NULL REFERENCES rule_sets(id),
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    clause_ref TEXT NOT NULL DEFAULT '<PLACEHOLDER: fill from handbook>',
    tier INT NOT NULL CHECK (tier IN (1, 2, 3)),
    severity TEXT DEFAULT 'medium',
    rectifiable BOOLEAN DEFAULT FALSE,
    clears_with TEXT,
    categories JSONB,  -- list of applicable categories
    definition JSONB NOT NULL,  -- the rule check definition
    depends_on_fields JSONB,  -- lineage: fields this rule reads
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- APPEND-ONLY: findings
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    source_code TEXT NOT NULL,  -- rule code
    tier INT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('TRUE', 'FALSE', 'UNKNOWN')),
    reason TEXT,
    evidence JSONB,
    recheck_recipe TEXT,
    depends_on_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- APPEND-ONLY: document_status
CREATE TABLE IF NOT EXISTS document_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    status TEXT NOT NULL CHECK (status IN (
        'VERIFICATION_PENDING', 'VERIFIED', 'MISMATCH_DETECTED',
        'EXPIRED', 'MANUAL_REVIEW_REQUIRED', 'SOURCE_UNAVAILABLE'
    )),
    source TEXT,
    result_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. Verification (APPEND-ONLY results)
-- ============================================================

CREATE TABLE IF NOT EXISTS verification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    application_id UUID NOT NULL REFERENCES applications(id),
    route TEXT NOT NULL,  -- 'signature', 'qr', 'reference_lookup', 'consented_fetch'
    issuer_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INT DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- APPEND-ONLY: verification_results
CREATE TABLE IF NOT EXISTS verification_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES verification_requests(id),
    source TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    responded_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    raw_hash TEXT,
    fields_compared JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consent_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id),
    granted_by UUID NOT NULL REFERENCES users(id),
    document_types JSONB NOT NULL,
    purpose TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. Indicators, Risk Scores, Links (MODEL-ONLY insert)
-- ============================================================

-- APPEND-ONLY: indicators
CREATE TABLE IF NOT EXISTS indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    detector TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 1),
    evidence JSONB,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- APPEND-ONLY: risk_scores
CREATE TABLE IF NOT EXISTS risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    score REAL NOT NULL CHECK (score >= 0 AND score <= 1),
    features JSONB,
    model_version TEXT,
    threshold_used REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL,
    record_a UUID NOT NULL,
    record_b UUID NOT NULL,
    match_probability REAL,
    match_weights JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 6. Review and Actions
-- ============================================================

CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    user_id UUID NOT NULL REFERENCES users(id),
    level INT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    level INT NOT NULL CHECK (level BETWEEN 0 AND 3),
    reason TEXT,
    assignee UUID REFERENCES users(id),
    state TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- APPEND-ONLY: reviewer_actions (correction #5)
CREATE TABLE IF NOT EXISTS reviewer_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id),
    action TEXT NOT NULL CHECK (action IN ('accept', 'dismiss')),
    reason TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reviewer notes: separate from audit chain for retention/crypto-shred
CREATE TABLE IF NOT EXISTS reviewer_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES findings(id),
    application_id UUID NOT NULL REFERENCES applications(id),
    note_text TEXT NOT NULL,
    note_hash TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. Alerts and Information Requests
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    application_id UUID REFERENCES applications(id),
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS information_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    requested_by UUID NOT NULL REFERENCES users(id),
    requested_from UUID REFERENCES institutions(id),
    document_or_field TEXT NOT NULL,
    reason TEXT NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    state TEXT NOT NULL DEFAULT 'OPEN' CHECK (state IN ('OPEN', 'ANSWERED', 'CLOSED', 'OVERDUE')),
    answered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 8. Claims (section 5.17 — proof-carrying self-disclosure)
-- ============================================================

CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    predicate TEXT NOT NULL,
    subject TEXT,
    value TEXT,
    unit TEXT,
    depends_on JSONB,  -- list of other claim ids
    state TEXT NOT NULL DEFAULT 'UNPROVEN' CHECK (state IN ('PROVEN', 'REFUTED', 'UNPROVEN', 'CONFLICTING')),
    strength INT,  -- highest tier among proving routes
    checked_by TEXT,
    last_checked TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    kind TEXT NOT NULL,  -- 'doc_span', 'issuer_ref', 'portal_record', etc.
    pointer JSONB NOT NULL,
    issuer_party TEXT,  -- for corroboration depth
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 9. System and Encryption
-- ============================================================

CREATE TABLE IF NOT EXISTS system_mode (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- singleton
    mode TEXT NOT NULL DEFAULT 'NORMAL' CHECK (mode IN ('NORMAL', 'DEGRADED')),
    since TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT
);
INSERT INTO system_mode (mode) VALUES ('NORMAL') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS file_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    encrypted_key BYTEA NOT NULL,
    nonce BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 10. Pipeline Job Queue (replaces Redis + RQ)
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    stage TEXT NOT NULL,
    payload JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    priority INT DEFAULT 0,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    worker_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_poll
    ON pipeline_jobs (priority DESC, created_at ASC)
    WHERE status = 'pending';

-- ============================================================
-- 11. Sealed Schema (canary monitor only)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS sealed;

CREATE TABLE IF NOT EXISTS sealed.canaries (
    application_id UUID PRIMARY KEY REFERENCES applications(id),
    manifest JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sealed.canary_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    expected_defects JSONB NOT NULL,
    actual_findings JSONB NOT NULL,
    machine_recall REAL,
    scored_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 12. Audit Log (APPEND-ONLY, hash chain)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    seq BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL,
    prev_hash TEXT NOT NULL DEFAULT '',
    hash TEXT NOT NULL
);

-- ============================================================
-- 13. Pre-check runs (section 16.1)
-- ============================================================

CREATE TABLE IF NOT EXISTS precheck_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    rule_codes JSONB,
    finding_counts JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 14. SECURITY DEFINER function: audit_append()
-- ============================================================

CREATE OR REPLACE FUNCTION audit_append(
    p_actor TEXT,
    p_action TEXT,
    p_payload JSONB
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_seq BIGINT;
    v_ts TIMESTAMPTZ;
    v_prev_hash TEXT;
    v_canonical TEXT;
    v_hash TEXT;
BEGIN
    -- Advisory lock to serialise chain appends
    PERFORM pg_advisory_xact_lock(42);

    -- Get the previous hash
    SELECT hash INTO v_prev_hash
    FROM audit_log
    ORDER BY seq DESC
    LIMIT 1;

    IF v_prev_hash IS NULL THEN
        v_prev_hash := '';
    END IF;

    v_ts := NOW();

    -- Get the next sequence value
    INSERT INTO audit_log (ts, actor, action, payload, prev_hash, hash)
    VALUES (v_ts, p_actor, p_action, p_payload, v_prev_hash, '')
    RETURNING seq INTO v_seq;

    -- Build canonical JSON: {"action":"...","actor":"...","payload":{...},"seq":N,"ts":"..."}
    -- Sorted keys, no spaces
    v_canonical := json_build_object(
        'action', p_action,
        'actor', p_actor,
        'payload', p_payload,
        'seq', v_seq,
        'ts', to_char(v_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"')
    )::TEXT;

    -- hash = SHA256(prev_hash || canonical_json)
    v_hash := encode(
        digest(convert_to(v_prev_hash || v_canonical, 'UTF8'), 'sha256'),
        'hex'
    );

    -- Update the hash (this is the ONLY update allowed on audit_log,
    -- done inside the SECURITY DEFINER function itself)
    UPDATE audit_log SET hash = v_hash WHERE seq = v_seq;

    RETURN v_seq;
END;
$$;

-- ============================================================
-- 15. PERMISSIONS: Append-only enforcement
-- ============================================================

-- Revoke all on append-only tables, then grant INSERT only
DO $$
DECLARE
    t TEXT;
    append_only_tables TEXT[] := ARRAY[
        'audit_log', 'findings', 'document_status',
        'verification_results', 'indicators', 'risk_scores',
        'reviewer_actions'
    ];
    all_roles TEXT[] := ARRAY[
        'app_api', 'app_det', 'app_model', 'app_monitor', 'app_readonly'
    ];
    r TEXT;
BEGIN
    FOREACH t IN ARRAY append_only_tables LOOP
        FOREACH r IN ARRAY all_roles LOOP
            EXECUTE format('REVOKE ALL ON %I FROM %I', t, r);
        END LOOP;
        -- Grant SELECT to all roles
        FOREACH r IN ARRAY all_roles LOOP
            EXECUTE format('GRANT SELECT ON %I TO %I', t, r);
        END LOOP;
    END LOOP;
END $$;

-- findings, document_status, verification_results: INSERT only by app_det
GRANT INSERT ON findings TO app_det;
GRANT INSERT ON document_status TO app_det;
GRANT INSERT ON verification_results TO app_det;

-- indicators, risk_scores: INSERT only by app_model
GRANT INSERT ON indicators TO app_model;
GRANT INSERT ON risk_scores TO app_model;

-- reviewer_actions: INSERT only by app_api (officers use the API)
GRANT INSERT ON reviewer_actions TO app_api;

-- audit_log: INSERT only via audit_append() SECURITY DEFINER
-- No direct INSERT grant to any role (the function runs as the owner)
GRANT EXECUTE ON FUNCTION audit_append(TEXT, TEXT, JSONB) TO app_api, app_det, app_model, app_monitor;

-- ============================================================
-- 16. PERMISSIONS: State-update tables (UPDATE allowed)
-- ============================================================

-- app_api gets broad access to state-update tables
GRANT SELECT, INSERT, UPDATE ON applications TO app_api;
GRANT SELECT, INSERT, UPDATE ON documents TO app_api;
GRANT SELECT, INSERT ON extracted_fields TO app_api;
GRANT SELECT, INSERT, UPDATE ON review_items TO app_api;
GRANT SELECT, INSERT ON reviewer_notes TO app_api;
GRANT SELECT, INSERT, UPDATE ON alerts TO app_api;
GRANT SELECT, INSERT, UPDATE ON information_requests TO app_api;
GRANT SELECT, INSERT, UPDATE ON verification_requests TO app_api;
GRANT SELECT, INSERT, UPDATE ON consent_artifacts TO app_api;
GRANT SELECT, INSERT, UPDATE ON claims TO app_api;
GRANT SELECT, INSERT ON claim_evidence TO app_api;
GRANT SELECT ON system_mode TO app_api;
GRANT SELECT ON rule_sets TO app_api;
GRANT SELECT ON rules TO app_api;
GRANT SELECT ON links TO app_api;
GRANT SELECT, INSERT ON precheck_runs TO app_api;
GRANT SELECT ON institutions TO app_api;
GRANT SELECT ON users TO app_api;

-- app_det gets access for pipeline writes
GRANT SELECT, INSERT, UPDATE ON applications TO app_det;
GRANT SELECT, INSERT, UPDATE ON documents TO app_det;
GRANT SELECT, INSERT ON extracted_fields TO app_det;
GRANT SELECT ON rule_sets TO app_det;
GRANT SELECT ON rules TO app_det;
GRANT SELECT, INSERT, UPDATE ON verification_requests TO app_det;
GRANT SELECT, INSERT, UPDATE ON claims TO app_det;
GRANT SELECT, INSERT ON claim_evidence TO app_det;
GRANT SELECT ON institutions TO app_det;

-- app_model
GRANT SELECT ON applications TO app_model;
GRANT SELECT ON documents TO app_model;
GRANT SELECT ON extracted_fields TO app_model;
GRANT SELECT ON findings TO app_model;
GRANT SELECT, INSERT ON links TO app_model;
GRANT SELECT, INSERT, UPDATE ON review_items TO app_model;
GRANT SELECT ON institutions TO app_model;

-- app_monitor: sealed schema + system_mode
GRANT USAGE ON SCHEMA sealed TO app_monitor;
GRANT SELECT, INSERT ON sealed.canaries TO app_monitor;
GRANT SELECT, INSERT ON sealed.canary_results TO app_monitor;
GRANT SELECT, UPDATE ON system_mode TO app_monitor;
GRANT SELECT ON applications TO app_monitor;
GRANT SELECT ON findings TO app_monitor;
GRANT SELECT ON indicators TO app_monitor;
GRANT SELECT ON institutions TO app_monitor;

-- app_readonly (auditor)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
-- Auditor cannot see sealed schema directly
-- (they see canary aggregate stats through the monitor API)

-- file_keys: DELETE allowed for crypto-shredding
GRANT SELECT, INSERT, DELETE ON file_keys TO app_api;
GRANT SELECT, INSERT ON file_keys TO app_det;

-- Pipeline jobs: the worker roles need to poll and update
GRANT SELECT, INSERT, UPDATE ON pipeline_jobs TO app_api, app_det, app_model;

-- Sequence grants for INSERT
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_api, app_det, app_model, app_monitor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA sealed TO app_monitor;

-- ============================================================
-- 17. ROW LEVEL SECURITY (forced, even for table owner)
-- ============================================================

-- Applications: institution users see only their own
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications FORCE ROW LEVEL SECURITY;

CREATE POLICY app_institution_isolation ON applications
    USING (
        current_setting('app.role', true) IN ('scrutiny_officer', 'supervisor', 'auditor', 'sysadmin', 'rules_admin')
        OR institution_id = current_setting('app.institution_id', true)::UUID
    );

-- Documents: follows application visibility
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY doc_institution_isolation ON documents
    USING (
        current_setting('app.role', true) IN ('scrutiny_officer', 'supervisor', 'auditor', 'sysadmin', 'rules_admin')
        OR application_id IN (
            SELECT id FROM applications
            WHERE institution_id = current_setting('app.institution_id', true)::UUID
        )
    );

-- Findings: follows application visibility
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings FORCE ROW LEVEL SECURITY;

CREATE POLICY findings_institution_isolation ON findings
    USING (
        current_setting('app.role', true) IN ('scrutiny_officer', 'supervisor', 'auditor', 'sysadmin', 'rules_admin')
        OR application_id IN (
            SELECT id FROM applications
            WHERE institution_id = current_setting('app.institution_id', true)::UUID
        )
    );

-- Assignments: officer sees only their assignments
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments FORCE ROW LEVEL SECURITY;

CREATE POLICY assignment_visibility ON assignments
    USING (
        current_setting('app.role', true) IN ('supervisor', 'auditor', 'sysadmin')
        OR user_id = current_setting('app.user_id', true)::UUID
    );

-- ============================================================
-- 18. Deny sealed schema to everyone except app_monitor
-- ============================================================
REVOKE ALL ON SCHEMA sealed FROM app_api, app_det, app_model, app_readonly;
REVOKE ALL ON ALL TABLES IN SCHEMA sealed FROM app_api, app_det, app_model, app_readonly;

-- ============================================================
-- 19. Rules admin: draft/approve
-- ============================================================
GRANT SELECT, INSERT, UPDATE ON rule_sets TO app_api;
GRANT SELECT, INSERT, UPDATE ON rules TO app_api;
"""


def run_sql(sql: str, db: str = DB_NAME) -> None:
    """Execute SQL against the database using psql."""
    psql = os.path.join(PG_BIN, "psql") if PG_BIN else "psql"
    result = subprocess.run(
        [psql, "-v", "ON_ERROR_STOP=1", db],
        input=sql,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"STDERR:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    if result.stdout:
        print(result.stdout)


def main():
    print(f"Setting up database '{DB_NAME}'...")
    run_sql(SCHEMA_SQL)
    print("✅ Database schema, roles, RLS policies, and audit chain created.")


if __name__ == "__main__":
    main()
