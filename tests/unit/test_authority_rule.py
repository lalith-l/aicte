"""GATE TEST: Authority rule — models cannot write findings or statuses.

This test MUST pass before Phase 1 starts.

Tests:
1. app_model INSERT into findings → must fail
2. app_model INSERT into document_status → must fail
3. app_model INSERT into verification_results → must fail
4. app_det INSERT into indicators → must fail
5. app_det INSERT into risk_scores → must fail
6. app_det CAN insert findings (positive test)
7. app_model CAN insert indicators (positive test)
8. reviewer_actions is insert-only: UPDATE must fail, DELETE must fail
9. No UPDATE or DELETE on audit_log for any role
10. No UPDATE or DELETE on findings for any role
"""
import pytest
import psycopg2


pytestmark = pytest.mark.gate


class TestAuthorityRule:
    """Models cannot write findings or statuses. Deterministic code cannot write indicators."""

    def test_model_cannot_insert_findings(self, db_model, seeded_application):
        """app_model INSERT into findings → must fail."""
        cur = db_model.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO findings (application_id, source_code, tier, result) "
                "VALUES (%s, 'TEST-001', 1, 'FALSE')",
                (seeded_application,)
            )

    def test_model_cannot_insert_document_status(self, db_model, seeded_application, db_superuser):
        """app_model INSERT into document_status → must fail."""
        # First create a document as superuser
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO documents (application_id, file_ref, sha256) "
            "VALUES (%s, 'test.pdf', 'abc123') RETURNING id",
            (seeded_application,)
        )
        doc_id = cur_su.fetchone()[0]
        db_superuser.commit()

        cur = db_model.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO document_status (document_id, status, source) "
                "VALUES (%s, 'VERIFIED', 'test')",
                (doc_id,)
            )

    def test_model_cannot_insert_verification_results(self, db_model, seeded_application, db_superuser):
        """app_model INSERT into verification_results → must fail."""
        # Create a verification request as superuser
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO documents (application_id, file_ref, sha256) "
            "VALUES (%s, 'test.pdf', 'abc456') RETURNING id",
            (seeded_application,)
        )
        doc_id = cur_su.fetchone()[0]
        cur_su.execute(
            "INSERT INTO verification_requests (document_id, application_id, route) "
            "VALUES (%s, %s, 'signature') RETURNING id",
            (doc_id, seeded_application)
        )
        req_id = cur_su.fetchone()[0]
        db_superuser.commit()

        cur = db_model.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO verification_results (request_id, source, requested_at, status) "
                "VALUES (%s, 'test', NOW(), 'valid')",
                (req_id,)
            )

    def test_det_cannot_insert_indicators(self, db_det, seeded_application):
        """app_det INSERT into indicators → must fail."""
        cur = db_det.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO indicators (application_id, detector, score) "
                "VALUES (%s, 'test_det', 0.5)",
                (seeded_application,)
            )

    def test_det_cannot_insert_risk_scores(self, db_det, seeded_application):
        """app_det INSERT into risk_scores → must fail."""
        cur = db_det.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO risk_scores (application_id, score) "
                "VALUES (%s, 0.5)",
                (seeded_application,)
            )

    def test_det_can_insert_findings(self, db_det, seeded_application, seeded_institution):
        """app_det CAN insert findings (positive test)."""
        cur = db_det.cursor()
        # app_det needs RLS context since findings has FORCE ROW LEVEL SECURITY
        cur.execute("SET LOCAL app.role = 'scrutiny_officer'")
        cur.execute("SET LOCAL app.institution_id = %s", (seeded_institution,))
        cur.execute(
            "INSERT INTO findings (application_id, source_code, tier, result) "
            "VALUES (%s, 'TEST-001', 1, 'FALSE') RETURNING id",
            (seeded_application,)
        )
        row = cur.fetchone()
        assert row is not None
        db_det.rollback()

    def test_model_can_insert_indicators(self, db_model, seeded_application):
        """app_model CAN insert indicators (positive test)."""
        cur = db_model.cursor()
        cur.execute(
            "INSERT INTO indicators (application_id, detector, score) "
            "VALUES (%s, 'test_det', 0.5) RETURNING id",
            (seeded_application,)
        )
        row = cur.fetchone()
        assert row is not None
        db_model.rollback()


class TestAppendOnlyTables:
    """Append-only tables reject UPDATE and DELETE for all roles."""

    @pytest.mark.parametrize("role_fixture", ["db_api", "db_det", "db_model"])
    def test_cannot_update_audit_log(self, role_fixture, request):
        """No role can UPDATE audit_log."""
        conn = request.getfixturevalue(role_fixture)
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("UPDATE audit_log SET action = 'hacked' WHERE seq = 1")

    @pytest.mark.parametrize("role_fixture", ["db_api", "db_det", "db_model"])
    def test_cannot_delete_audit_log(self, role_fixture, request):
        """No role can DELETE from audit_log."""
        conn = request.getfixturevalue(role_fixture)
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM audit_log WHERE seq = 1")

    @pytest.mark.parametrize("role_fixture", ["db_api", "db_det", "db_model"])
    def test_cannot_update_findings(self, role_fixture, request):
        """No role can UPDATE findings."""
        conn = request.getfixturevalue(role_fixture)
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("UPDATE findings SET result = 'TRUE' WHERE id = gen_random_uuid()")

    @pytest.mark.parametrize("role_fixture", ["db_api", "db_det", "db_model"])
    def test_cannot_delete_findings(self, role_fixture, request):
        """No role can DELETE from findings."""
        conn = request.getfixturevalue(role_fixture)
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM findings WHERE id = gen_random_uuid()")

    def test_reviewer_actions_no_update(self, db_api, seeded_application, db_superuser):
        """reviewer_actions is insert-only: UPDATE must fail (correction #5)."""
        # Create a finding as det
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO findings (application_id, source_code, tier, result) "
            "VALUES (%s, 'TEST-RA', 1, 'FALSE') RETURNING id",
            (seeded_application,)
        )
        finding_id = cur_su.fetchone()[0]

        # Create a user for the action
        cur_su.execute(
            "SELECT id FROM users LIMIT 1"
        )
        row = cur_su.fetchone()
        if not row:
            cur_su.execute(
                "INSERT INTO institutions (name, code) VALUES ('RA Test', 'RA001') RETURNING id"
            )
            inst_id = cur_su.fetchone()[0]
            cur_su.execute(
                "INSERT INTO users (username, email, pw_hash, role, institution_id) "
                "VALUES ('ra_test', 'ra@test.com', 'hash', 'scrutiny_officer', %s) RETURNING id",
                (inst_id,)
            )
            user_id = cur_su.fetchone()[0]
        else:
            user_id = row[0]
        db_superuser.commit()

        # Insert a reviewer action
        cur_api = db_api.cursor()
        cur_api.execute(
            "INSERT INTO reviewer_actions (finding_id, action, reason, user_id) "
            "VALUES (%s, 'accept', 'looks correct', %s) RETURNING id",
            (finding_id, user_id)
        )
        action_id = cur_api.fetchone()[0]
        db_api.commit()

        # UPDATE must fail
        cur_api2 = db_api.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur_api2.execute(
                "UPDATE reviewer_actions SET reason = 'changed' WHERE id = %s",
                (action_id,)
            )

    def test_reviewer_actions_no_delete(self, db_api):
        """reviewer_actions is insert-only: DELETE must fail (correction #5)."""
        cur = db_api.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM reviewer_actions WHERE id = gen_random_uuid()")


class TestStateUpdateTablesAllowUpdate:
    """Tables that need state transitions DO allow UPDATE."""

    def test_can_update_application_stage(self, db_api, seeded_application):
        """applications.stage can be updated (state machine)."""
        cur = db_api.cursor()
        # Set RLS context
        cur.execute("SET LOCAL app.role = 'scrutiny_officer'")
        cur.execute(
            "UPDATE applications SET stage = 'INGESTING' WHERE id = %s",
            (seeded_application,)
        )
        assert cur.rowcount == 1
        db_api.rollback()

    def test_can_update_alert_acknowledgement(self, db_api, db_superuser, seeded_application):
        """alerts can be updated for acknowledgement."""
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO alerts (type, application_id, message) "
            "VALUES ('missing_info', %s, 'test') RETURNING id",
            (seeded_application,)
        )
        alert_id = cur_su.fetchone()[0]
        db_superuser.commit()

        cur = db_api.cursor()
        cur.execute(
            "UPDATE alerts SET delivered_at = NOW() WHERE id = %s",
            (alert_id,)
        )
        assert cur.rowcount == 1
        db_api.rollback()

    def test_can_delete_file_keys(self, db_api, db_superuser, seeded_application):
        """file_keys DELETE is allowed for crypto-shredding."""
        cur_su = db_superuser.cursor()
        cur_su.execute(
            "INSERT INTO documents (application_id, file_ref, sha256) "
            "VALUES (%s, 'test.pdf', 'shred123') RETURNING id",
            (seeded_application,)
        )
        doc_id = cur_su.fetchone()[0]
        cur_su.execute(
            "INSERT INTO file_keys (document_id, encrypted_key, nonce) "
            "VALUES (%s, '\\x0102', '\\x0304') RETURNING id",
            (doc_id,)
        )
        key_id = cur_su.fetchone()[0]
        db_superuser.commit()

        cur = db_api.cursor()
        cur.execute("DELETE FROM file_keys WHERE id = %s", (key_id,))
        assert cur.rowcount == 1
        db_api.rollback()
