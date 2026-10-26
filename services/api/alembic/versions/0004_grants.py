"""Grants discovered while wiring the API.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL = r"""
-- login lockout counters (column-level: app_api can touch nothing else on users)
GRANT UPDATE (failed_login_count, locked_until) ON users TO app_api;
"""


def upgrade() -> None:
    cur = op.get_bind().connection.cursor()
    cur.execute(SQL)
    cur.close()


def downgrade() -> None:
    raise NotImplementedError("Forward-only migration.")
