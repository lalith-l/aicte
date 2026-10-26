"""Allow UNREADABLE document_status (encrypted PDF gate) and MAINTENANCE mode.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL = r"""
ALTER TABLE document_status DROP CONSTRAINT IF EXISTS document_status_status_check;
ALTER TABLE document_status ADD CONSTRAINT document_status_status_check
  CHECK (status IN (
    'VERIFICATION_PENDING', 'VERIFIED', 'MISMATCH_DETECTED',
    'EXPIRED', 'MANUAL_REVIEW_REQUIRED', 'SOURCE_UNAVAILABLE', 'UNREADABLE'
  ));

ALTER TABLE system_mode DROP CONSTRAINT IF EXISTS system_mode_mode_check;
ALTER TABLE system_mode ADD CONSTRAINT system_mode_mode_check
  CHECK (mode IN ('NORMAL', 'DEGRADED', 'MAINTENANCE'));

GRANT SELECT ON audit_log TO app_api, app_readonly, app_monitor;
GRANT EXECUTE ON FUNCTION audit_append(TEXT, TEXT, JSONB) TO app_readonly;
"""


def upgrade() -> None:
    cur = op.get_bind().connection.cursor()
    cur.execute(SQL)
    cur.close()


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration.")
