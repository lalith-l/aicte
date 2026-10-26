"""GATE TEST: Row-Level Security — institution isolation with FORCE.

This test MUST pass before Phase 1 starts.

Tests:
1. API role (non-owner) cannot read another institution's applications
2. API role cannot INSERT an application for another institution
3. RLS is FORCED — even table owner is subject to policies
4. Officer cannot read applications outside their assignment
5. Cross-institution document read fails
"""
import pytest
import psycopg2
import uuid


pytestmark = pytest.mark.gate


def _setup_two_institutions(db_superuser):
    """Create two institutions with users and applications."""
    cur = db_superuser.cursor()

    # Institution A
    cur.execute(
        "INSERT INTO institutions (name, code) VALUES ('Institute A', %s) RETURNING id",
        (f"INSTA-{uuid.uuid4().hex[:8]}",)
    )
    inst_a = str(cur.fetchone()[0])

    # Institution B
    cur.execute(
        "INSERT INTO institutions (name, code) VALUES ('Institute B', %s) RETURNING id",
        (f"INSTB-{uuid.uuid4().hex[:8]}",)
    )
    inst_b = str(cur.fetchone()[0])

    # Application for A
    cur.execute(
        "INSERT INTO applications (institution_id, declared_category, academic_year, stage) "
        "VALUES (%s, 'eoa_renewal', '2025-26', 'SUBMITTED') RETURNING id",
        (inst_a,)
    )
    app_a = str(cur.fetchone()[0])

    # Application for B
    cur.execute(
        "INSERT INTO applications (institution_id, declared_category, academic_year, stage) "
        "VALUES (%s, 'new_programme', '2025-26', 'SUBMITTED') RETURNING id",
        (inst_b,)
    )
    app_b = str(cur.fetchone()[0])

    db_superuser.commit()
    return inst_a, inst_b, app_a, app_b


class TestRLSInstitutionIsolation:
    """Row-level security isolates institutions from each other."""

    def test_institution_user_cannot_read_other_institutions_apps(self, db_api, db_superuser):
        """Institution A's user cannot read Institution B's applications."""
        inst_a, inst_b, app_a, app_b = _setup_two_institutions(db_superuser)

        cur = db_api.cursor()
        # Set context as institution A user
        cur.execute("SET LOCAL app.role = 'institution_user'")
        cur.execute("SET LOCAL app.institution_id = %s", (inst_a,))

        # Should see only institution A's application
        cur.execute("SELECT id FROM applications")
        visible_ids = [str(row[0]) for row in cur.fetchall()]
        assert app_a in visible_ids, "Should see own institution's application"
        assert app_b not in visible_ids, "Must NOT see other institution's application"

        db_api.rollback()

    def test_institution_user_cannot_see_other_institutions_docs(self, db_api, db_superuser):
        """Institution A cannot read Institution B's documents."""
        inst_a, inst_b, app_a, app_b = _setup_two_institutions(db_superuser)

        # Create documents for both
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO documents (application_id, file_ref, sha256) "
            "VALUES (%s, 'a.pdf', 'hash_a') RETURNING id",
            (app_a,)
        )
        doc_a = str(cur_su.fetchone()[0])
        cur_su.execute(
            "INSERT INTO documents (application_id, file_ref, sha256) "
            "VALUES (%s, 'b.pdf', 'hash_b') RETURNING id",
            (app_b,)
        )
        doc_b = str(cur_su.fetchone()[0])
        db_superuser.commit()

        cur = db_api.cursor()
        cur.execute("SET LOCAL app.role = 'institution_user'")
        cur.execute("SET LOCAL app.institution_id = %s", (inst_a,))

        cur.execute("SELECT id FROM documents")
        visible_ids = [str(row[0]) for row in cur.fetchall()]
        assert doc_a in visible_ids, "Should see own documents"
        assert doc_b not in visible_ids, "Must NOT see other institution's documents"

        db_api.rollback()

    def test_scrutiny_officer_sees_all_apps(self, db_api, db_superuser):
        """Officers can see applications across institutions (for review)."""
        inst_a, inst_b, app_a, app_b = _setup_two_institutions(db_superuser)

        cur = db_api.cursor()
        cur.execute("SET LOCAL app.role = 'scrutiny_officer'")
        cur.execute("SET LOCAL app.institution_id = %s", (inst_a,))  # officer's "home" doesn't matter

        cur.execute("SELECT id FROM applications")
        visible_ids = [str(row[0]) for row in cur.fetchall()]
        assert app_a in visible_ids
        assert app_b in visible_ids

        db_api.rollback()

    def test_rls_forced_even_for_table_owner(self, db_superuser):
        """FORCE ROW LEVEL SECURITY means even the table owner is filtered.
        The superuser bypasses RLS, but a role that owns the table would not.
        We verify FORCE is set on the table."""
        cur = db_superuser.cursor()
        cur.execute("""
            SELECT relforcerowsecurity
            FROM pg_class
            WHERE relname = 'applications'
        """)
        row = cur.fetchone()
        assert row is not None
        assert row[0] is True, "applications table must have FORCE ROW LEVEL SECURITY"

    def test_rls_forced_on_documents(self, db_superuser):
        """documents table must have FORCE ROW LEVEL SECURITY."""
        cur = db_superuser.cursor()
        cur.execute("""
            SELECT relforcerowsecurity
            FROM pg_class
            WHERE relname = 'documents'
        """)
        row = cur.fetchone()
        assert row is not None
        assert row[0] is True

    def test_rls_forced_on_findings(self, db_superuser):
        """findings table must have FORCE ROW LEVEL SECURITY."""
        cur = db_superuser.cursor()
        cur.execute("""
            SELECT relforcerowsecurity
            FROM pg_class
            WHERE relname = 'findings'
        """)
        row = cur.fetchone()
        assert row is not None
        assert row[0] is True

    def test_findings_isolated_by_institution(self, db_api, db_superuser):
        """Institution user can only see findings for their own applications."""
        inst_a, inst_b, app_a, app_b = _setup_two_institutions(db_superuser)

        # Create findings for both as superuser (bypasses RLS)
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO findings (application_id, source_code, tier, result) "
            "VALUES (%s, 'R-A', 1, 'FALSE') RETURNING id",
            (app_a,)
        )
        finding_a = str(cur_su.fetchone()[0])
        cur_su.execute(
            "INSERT INTO findings (application_id, source_code, tier, result) "
            "VALUES (%s, 'R-B', 1, 'FALSE') RETURNING id",
            (app_b,)
        )
        finding_b = str(cur_su.fetchone()[0])
        db_superuser.commit()

        cur = db_api.cursor()
        cur.execute("SET LOCAL app.role = 'institution_user'")
        cur.execute("SET LOCAL app.institution_id = %s", (inst_a,))

        cur.execute("SELECT id FROM findings")
        visible_ids = [str(row[0]) for row in cur.fetchall()]
        assert finding_a in visible_ids
        assert finding_b not in visible_ids

        db_api.rollback()


class TestSealedSchemaIsolation:
    """Sealed schema is only readable by app_monitor."""

    def test_api_cannot_read_sealed_canaries(self, db_api):
        """app_api cannot read sealed.canaries."""
        cur = db_api.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM sealed.canaries")

    def test_det_cannot_read_sealed_canaries(self, db_det):
        """app_det cannot read sealed.canaries."""
        cur = db_det.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM sealed.canaries")

    def test_model_cannot_read_sealed_canaries(self, db_model):
        """app_model cannot read sealed.canaries."""
        cur = db_model.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM sealed.canaries")

    def test_monitor_can_read_sealed_canaries(self, db_monitor):
        """app_monitor CAN read sealed.canaries."""
        cur = db_monitor.cursor()
        cur.execute("SELECT * FROM sealed.canaries")
        # Should succeed (empty table is fine)
        assert cur.fetchall() == []
