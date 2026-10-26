"""Hardening: audit_verify(), complete forced RLS, sealed canary flag, eval ground
truth, reports table, extra columns for findings/alerts/verification.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = r"""
-- ------------------------------------------------------------------
-- 1. RLS helper functions (SECURITY DEFINER => no nested-RLS recursion)
-- ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION app_is_staff() RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT coalesce(current_setting('app.role', true), '') IN
    ('scrutiny_officer','supervisor','auditor','sysadmin','rules_admin','pipeline')
$$;

CREATE OR REPLACE FUNCTION app_inst_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.institution_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION app_can_see_application(p_app uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app_is_staff() OR EXISTS (
    SELECT 1 FROM applications a
    WHERE a.id = p_app AND a.institution_id = app_inst_id())
$$;

CREATE OR REPLACE FUNCTION app_can_see_document(p_doc uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app_is_staff() OR EXISTS (
    SELECT 1 FROM documents d JOIN applications a ON a.id = d.application_id
    WHERE d.id = p_doc AND a.institution_id = app_inst_id())
$$;

CREATE OR REPLACE FUNCTION app_can_see_request(p_req uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app_is_staff() OR EXISTS (
    SELECT 1 FROM verification_requests r JOIN applications a ON a.id = r.application_id
    WHERE r.id = p_req AND a.institution_id = app_inst_id())
$$;

-- ------------------------------------------------------------------
-- 2. Canary flag leaves the public schema (staff must not be able to
--    tell canaries from real institutions).
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sealed.canary_institutions (
    institution_id UUID PRIMARY KEY REFERENCES institutions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='institutions' AND column_name='is_canary') THEN
    INSERT INTO sealed.canary_institutions (institution_id)
      SELECT id FROM institutions WHERE is_canary ON CONFLICT DO NOTHING;
    ALTER TABLE institutions DROP COLUMN is_canary;
  END IF;
END $$;
GRANT SELECT, INSERT ON sealed.canary_institutions TO app_monitor;
REVOKE ALL ON sealed.canary_institutions FROM app_api, app_det, app_model, app_readonly;

-- ------------------------------------------------------------------
-- 3. Evaluation ground truth (never readable by application roles)
-- ------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS eval;
CREATE TABLE IF NOT EXISTS eval.ground_truth (
    application_id UUID PRIMARY KEY REFERENCES applications(id),
    split TEXT NOT NULL CHECK (split IN ('dev','calibration','test','canary','demo')),
    defects JSONB NOT NULL DEFAULT '[]',
    scan_level INT,
    meta JSONB
);
REVOKE ALL ON SCHEMA eval FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA eval FROM app_api, app_det, app_model, app_readonly, app_monitor;

-- ------------------------------------------------------------------
-- 4. Column additions
-- ------------------------------------------------------------------
ALTER TABLE findings ADD COLUMN IF NOT EXISTS clause_ref TEXT DEFAULT 'PLACEHOLDER';
ALTER TABLE findings ADD COLUMN IF NOT EXISTS rectifiable BOOLEAN DEFAULT TRUE;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS provisional BOOLEAN DEFAULT TRUE;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS ruleset_id UUID;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity TEXT DEFAULT 'medium';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS institution_id UUID;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS reference_number TEXT;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS ps_status TEXT;
ALTER TABLE rules ADD COLUMN IF NOT EXISTS parameters JSONB;
ALTER TABLE rules ADD COLUMN IF NOT EXISTS kind TEXT;
ALTER TABLE rule_sets ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE rule_sets ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS scan_level INT;

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    schema_version TEXT NOT NULL,
    report_json JSONB NOT NULL,
    json_hash TEXT NOT NULL,
    pdf_ref TEXT,
    pdf_hash TEXT,
    generated_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_app ON reports(application_id, created_at DESC);

-- Grants for new/extended objects
GRANT SELECT ON reports TO app_api, app_readonly, app_monitor;
GRANT SELECT, INSERT ON reports TO app_det;
GRANT SELECT, INSERT, UPDATE ON alerts TO app_det;
GRANT SELECT, INSERT, UPDATE ON review_items TO app_det;
GRANT SELECT, INSERT ON information_requests TO app_det;
GRANT SELECT ON document_status TO app_api;
GRANT SELECT ON extracted_fields TO app_model;
GRANT SELECT ON verification_requests TO app_model;
GRANT SELECT ON consent_artifacts TO app_det;
GRANT SELECT ON users TO app_det;
GRANT SELECT, INSERT, UPDATE ON rule_sets TO app_det;
GRANT SELECT, INSERT, UPDATE ON rules TO app_det;
GRANT SELECT, INSERT, UPDATE ON precheck_runs TO app_det;
GRANT SELECT, INSERT, UPDATE ON system_mode TO app_det;
GRANT UPDATE ON system_mode TO app_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON file_keys TO app_det;
GRANT SELECT ON file_keys TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

-- ------------------------------------------------------------------
-- 5. Complete forced RLS
-- ------------------------------------------------------------------
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'institutions','extracted_fields','document_status','verification_requests',
    'verification_results','alerts','information_requests','review_items',
    'reviewer_actions','reviewer_notes','indicators','risk_scores','links',
    'claims','claim_evidence','precheck_runs','consent_artifacts','reports','file_keys'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

-- Replace the baseline policies with NULL-safe equivalents
DROP POLICY IF EXISTS app_institution_isolation ON applications;
CREATE POLICY app_institution_isolation ON applications
  USING (app_is_staff() OR institution_id = app_inst_id());

DROP POLICY IF EXISTS doc_institution_isolation ON documents;
CREATE POLICY doc_institution_isolation ON documents
  USING (app_can_see_application(application_id));

-- Institution users never see Tier 3 findings (forensic detail is not disclosed)
DROP POLICY IF EXISTS findings_institution_isolation ON findings;
CREATE POLICY findings_institution_isolation ON findings
  USING (app_is_staff() OR (tier <= 2 AND app_can_see_application(application_id)));

DROP POLICY IF EXISTS assignment_visibility ON assignments;
CREATE POLICY assignment_visibility ON assignments
  USING (coalesce(current_setting('app.role', true),'') IN ('supervisor','auditor','sysadmin','pipeline')
         OR user_id = nullif(current_setting('app.user_id', true), '')::uuid);

CREATE POLICY inst_rls ON institutions USING (app_is_staff() OR id = app_inst_id());
CREATE POLICY ef_rls ON extracted_fields USING (app_can_see_document(document_id));
CREATE POLICY ds_rls ON document_status USING (app_can_see_document(document_id));
CREATE POLICY vr_rls ON verification_requests USING (app_can_see_application(application_id));
CREATE POLICY vres_rls ON verification_results USING (app_can_see_request(request_id));
CREATE POLICY ir_rls ON information_requests USING (app_can_see_application(application_id));
CREATE POLICY consent_rls ON consent_artifacts USING (app_is_staff() OR institution_id = app_inst_id());
CREATE POLICY pc_rls ON precheck_runs USING (app_can_see_application(application_id));
CREATE POLICY claims_rls ON claims USING (app_can_see_application(application_id));
CREATE POLICY claim_ev_rls ON claim_evidence USING (app_is_staff());
CREATE POLICY fk_rls ON file_keys USING (app_is_staff());
-- Staff-only tables (institution users must never read them)
CREATE POLICY alerts_rls ON alerts USING (app_is_staff());
CREATE POLICY review_rls ON review_items USING (app_is_staff());
CREATE POLICY ra_rls ON reviewer_actions USING (app_is_staff());
CREATE POLICY rn_rls ON reviewer_notes USING (app_is_staff());
CREATE POLICY ind_rls ON indicators USING (app_is_staff());
CREATE POLICY risk_rls ON risk_scores USING (app_is_staff());
CREATE POLICY links_rls ON links USING (app_is_staff());
CREATE POLICY reports_rls ON reports USING (app_is_staff());

-- ------------------------------------------------------------------
-- 6. Audit chain verification (recomputes exactly what audit_append hashed)
-- ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit_verify()
RETURNS TABLE (ok boolean, broken_seq bigint, entries bigint, head_seq bigint, head_hash text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
  r RECORD;
  v_prev TEXT := '';
  v_expected TEXT;
  v_count BIGINT := 0;
  v_last_seq BIGINT;
  v_last_hash TEXT;
BEGIN
  FOR r IN SELECT * FROM audit_log ORDER BY seq ASC LOOP
    v_count := v_count + 1;
    IF r.prev_hash IS DISTINCT FROM v_prev THEN
      RETURN QUERY SELECT false, r.seq, v_count, r.seq, r.hash; RETURN;
    END IF;
    v_expected := encode(digest(convert_to(r.prev_hash || json_build_object(
        'action', r.action, 'actor', r.actor, 'payload', r.payload, 'seq', r.seq,
        'ts', to_char(r.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"')
      )::TEXT, 'UTF8'), 'sha256'), 'hex');
    IF v_expected IS DISTINCT FROM r.hash THEN
      RETURN QUERY SELECT false, r.seq, v_count, r.seq, r.hash; RETURN;
    END IF;
    v_prev := r.hash; v_last_seq := r.seq; v_last_hash := r.hash;
  END LOOP;
  RETURN QUERY SELECT true, NULL::bigint, v_count, v_last_seq, coalesce(v_last_hash, '');
END $$;

CREATE OR REPLACE FUNCTION audit_head()
RETURNS TABLE (head_seq bigint, head_hash text, entries bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT coalesce(max(seq), 0), coalesce((SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1), ''), count(*)
  FROM audit_log
$$;
GRANT EXECUTE ON FUNCTION audit_verify(), audit_head() TO app_api, app_det, app_model, app_monitor, app_readonly;
"""


def upgrade() -> None:
    cur = op.get_bind().connection.cursor()
    cur.execute(SQL)
    cur.close()


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration.")
