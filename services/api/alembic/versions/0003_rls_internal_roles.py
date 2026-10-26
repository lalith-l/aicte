"""RLS refinement: internal DB roles bypass via TO-scoped policy; staff-only tables
block only an explicit institution_user context (API sets the role from the JWT on
every request); institution-facing tables stay fail-closed.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL = r"""
CREATE OR REPLACE FUNCTION app_not_institution() RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT coalesce(current_setting('app.role', true), '') <> 'institution_user'
$$;

DO $$
DECLARE t TEXT;
BEGIN
  -- staff-only tables: only an explicit institution_user context is denied
  FOREACH t IN ARRAY ARRAY['alerts','review_items','reviewer_actions','reviewer_notes',
                           'indicators','risk_scores','links','reports','file_keys','claim_evidence']
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I',
      CASE t WHEN 'alerts' THEN 'alerts_rls' WHEN 'review_items' THEN 'review_rls'
             WHEN 'reviewer_actions' THEN 'ra_rls' WHEN 'reviewer_notes' THEN 'rn_rls'
             WHEN 'indicators' THEN 'ind_rls' WHEN 'risk_scores' THEN 'risk_rls'
             WHEN 'links' THEN 'links_rls' WHEN 'reports' THEN 'reports_rls'
             WHEN 'file_keys' THEN 'fk_rls' ELSE 'claim_ev_rls' END, t);
    EXECUTE format('CREATE POLICY staff_only ON %I USING (app_not_institution())', t);
  END LOOP;

  -- internal pipeline / monitor / auditor DB roles: not governed by the session GUC
  FOREACH t IN ARRAY ARRAY['applications','documents','findings','assignments','institutions',
      'extracted_fields','document_status','verification_requests','verification_results',
      'alerts','information_requests','review_items','reviewer_actions','reviewer_notes',
      'indicators','risk_scores','links','claims','claim_evidence','precheck_runs',
      'consent_artifacts','reports','file_keys']
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS internal_roles ON %I', t);
    EXECUTE format('CREATE POLICY internal_roles ON %I FOR ALL TO app_det, app_model, app_monitor, app_readonly USING (true) WITH CHECK (true)', t);
  END LOOP;
END $$;
"""


def upgrade() -> None:
    cur = op.get_bind().connection.cursor()
    cur.execute(SQL)
    cur.close()


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration.")
