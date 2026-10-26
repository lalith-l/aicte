"""Phase 0.3 / 4.4: the REAL Postgres audit chain.

(1) tamper one entry  -> verifier fails at that seq
(2) recompute the whole chain after tampering -> internal verifier passes,
    but the published head hash fails.

Everything runs inside one transaction that is rolled back, so the real chain is never
altered. The tampering uses the superuser connection: application roles cannot UPDATE
audit_log at all (see test_authority_rule).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.audit.chain import check_published_head, verify_chain_db  # noqa: E402

pytestmark = pytest.mark.gate

RECOMPUTE_SQL = """
DO $$
DECLARE r RECORD; prev TEXT := ''; h TEXT;
BEGIN
  FOR r IN SELECT * FROM audit_log ORDER BY seq LOOP
    h := encode(digest(convert_to(prev || json_build_object(
        'action', r.action, 'actor', r.actor, 'payload', r.payload, 'seq', r.seq,
        'ts', to_char(r.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"'))::TEXT,
        'UTF8'), 'sha256'), 'hex');
    UPDATE audit_log SET prev_hash = prev, hash = h WHERE seq = r.seq;
    prev := h;
  END LOOP;
END $$;
"""


@pytest.fixture
def chain(db_superuser):
    cur = db_superuser.cursor()
    seqs = []
    for i in range(100):
        cur.execute(
            "SELECT audit_append(%s,%s,%s::jsonb)",
            (f"user_{i % 5}", f"test_action_{i % 3}", json.dumps({"i": i, "note": "synthetic"})),
        )
        seqs.append(cur.fetchone()[0])
    yield db_superuser, seqs
    db_superuser.rollback()


def test_100_entry_chain_verifies(chain):
    conn, seqs = chain
    st = verify_chain_db(conn)
    assert st.ok and st.broken_seq is None
    assert st.entries >= 100 and st.head_seq == seqs[-1]


def test_tamper_one_entry_fails_at_that_seq(chain):
    conn, seqs = chain
    target = seqs[50]
    cur = conn.cursor()
    cur.execute(
        "UPDATE audit_log SET payload = payload || '{\"tampered\": true}'::jsonb WHERE seq=%s",
        (target,),
    )
    st = verify_chain_db(conn)
    assert not st.ok
    assert st.broken_seq == target


def test_recomputed_chain_passes_internal_but_fails_published_head(chain):
    conn, seqs = chain
    # publish the head BEFORE anyone tampers
    cur = conn.cursor()
    cur.execute("SELECT head_seq, head_hash, entries FROM audit_head()")
    hs, hh, n = cur.fetchone()
    published = {"date": "2026-10-26", "head_seq": hs, "head_hash": hh, "entry_count": n}
    assert check_published_head(conn, published).ok

    # attacker edits an old entry, then recomputes every hash so the chain is self-consistent
    cur.execute(
        "UPDATE audit_log SET payload = payload || '{\"forged\": true}'::jsonb WHERE seq=%s",
        (seqs[10],),
    )
    assert not verify_chain_db(conn).ok
    cur.execute(RECOMPUTE_SQL)

    assert verify_chain_db(conn).ok, "internal verifier is fooled by a full recompute"
    res = check_published_head(conn, published)
    assert not res.ok, "published head hash must catch the rewrite"
    assert "MISMATCH" in res.message


def test_no_application_role_can_edit_audit_log(db_api, db_det, db_model):
    import psycopg2

    for conn in (db_api, db_det, db_model):
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("UPDATE audit_log SET actor='x'")
        conn.rollback()
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM audit_log")
        conn.rollback()
