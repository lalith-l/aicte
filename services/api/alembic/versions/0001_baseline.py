"""Baseline: roles, core tables, scoped append-only revokes, forced RLS, audit_append().

Reuses the SQL in scripts/setup_db.py so there is exactly one definition.
An existing database that was created by `scripts/setup_db.py` is brought under
Alembic with `alembic stamp 0001`.

Revision ID: 0001
Revises:
"""

import os
import sys

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def upgrade() -> None:
    from scripts.setup_db import SCHEMA_SQL

    cur = op.get_bind().connection.cursor()
    cur.execute(SCHEMA_SQL)
    cur.close()


def downgrade() -> None:
    raise NotImplementedError("Baseline cannot be downgraded; drop the database instead.")
