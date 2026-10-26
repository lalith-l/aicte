"""Shared test fixtures."""
import os
import pytest
import psycopg2

DB_NAME = os.environ.get("AICTE_DB_NAME", "aicte_validator")
PG_BIN = os.environ.get("PG_BIN", "/opt/homebrew/opt/postgresql@16/bin")
PG_HOST = os.environ.get("PG_HOST", "/tmp")

# Add packages to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _connect(role: str | None = None, dbname: str = DB_NAME) -> psycopg2.extensions.connection:
    """Connect to the database, optionally as a specific role."""
    if role:
        conn = psycopg2.connect(dbname=dbname, user=role, password=f"{role}_dev", host=PG_HOST)
    else:
        # Connect as the superuser (current OS user)
        conn = psycopg2.connect(dbname=dbname, host=PG_HOST)
    conn.autocommit = False
    return conn


@pytest.fixture
def db_superuser():
    """Connection as the database superuser (for setup/teardown)."""
    conn = _connect()
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_api():
    """Connection as the app_api role."""
    conn = _connect("app_api")
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_det():
    """Connection as the app_det role (deterministic writer)."""
    conn = _connect("app_det")
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_model():
    """Connection as the app_model role (model writer)."""
    conn = _connect("app_model")
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_monitor():
    """Connection as the app_monitor role."""
    conn = _connect("app_monitor")
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_readonly():
    """Connection as the app_readonly role (auditor)."""
    conn = _connect("app_readonly")
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def seeded_institution(db_superuser):
    """Create a test institution with a unique code and return its id."""
    import uuid
    code = f"TEST-{uuid.uuid4().hex[:8]}"
    cur = db_superuser.cursor()
    cur.execute(
        "INSERT INTO institutions (name, code) VALUES ('Test Institute', %s) RETURNING id",
        (code,)
    )
    inst_id = cur.fetchone()[0]
    db_superuser.commit()
    yield str(inst_id)
    # Full cascade cleanup — must go child-first
    db_superuser.rollback()  # clear any pending failed txn
    cur = db_superuser.cursor()
    cur.execute("SELECT id FROM applications WHERE institution_id = %s", (inst_id,))
    app_ids = [r[0] for r in cur.fetchall()]
    for aid in app_ids:
        cur.execute("DELETE FROM reviewer_actions WHERE finding_id IN (SELECT id FROM findings WHERE application_id=%s)", (aid,))
        cur.execute("DELETE FROM reviewer_notes WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM findings WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM indicators WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM risk_scores WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM alerts WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM review_items WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM information_requests WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM verification_results WHERE request_id IN (SELECT id FROM verification_requests WHERE application_id=%s)", (aid,))
        cur.execute("DELETE FROM verification_requests WHERE application_id=%s", (aid,))
        cur.execute("DELETE FROM document_status WHERE document_id IN (SELECT id FROM documents WHERE application_id=%s)", (aid,))
        cur.execute("DELETE FROM file_keys WHERE document_id IN (SELECT id FROM documents WHERE application_id=%s)", (aid,))
        cur.execute("DELETE FROM documents WHERE application_id=%s", (aid,))
    cur.execute("DELETE FROM applications WHERE institution_id = %s", (inst_id,))
    cur.execute("DELETE FROM institutions WHERE id = %s", (inst_id,))
    db_superuser.commit()
    cur.close()


@pytest.fixture
def seeded_application(db_superuser, seeded_institution):
    """Create a test application and return its id."""
    cur = db_superuser.cursor()
    cur.execute(
        "INSERT INTO applications (institution_id, declared_category, academic_year, stage) "
        "VALUES (%s, 'eoa_renewal', '2025-26', 'SUBMITTED') RETURNING id",
        (seeded_institution,)
    )
    app_id = cur.fetchone()[0]
    db_superuser.commit()
    yield str(app_id)
    cur.close()

