"""Phase 0.5: Postgres job queue — enqueue/dequeue, SKIP LOCKED exclusivity."""

from __future__ import annotations

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.common import jobqueue  # noqa: E402
from tests.conftest import _connect  # noqa: E402

pytestmark = pytest.mark.gate


@pytest.fixture
def clean_jobs(db_superuser, seeded_application):
    yield seeded_application
    db_superuser.rollback()
    cur = db_superuser.cursor()
    cur.execute("DELETE FROM pipeline_jobs WHERE application_id=%s", (seeded_application,))
    db_superuser.commit()


def test_enqueue_dequeue_roundtrip(db_det, db_superuser, clean_jobs):
    app_id = clean_jobs
    # isolate from other pending jobs by giving ours top priority
    jid = jobqueue.enqueue(db_det, app_id, "INGEST", {"k": 1}, priority=10_000)
    db_det.commit()
    job = jobqueue.dequeue(db_det, "worker-t")
    db_det.commit()
    assert job and job["id"] == jid and job["stage"] == "INGEST" and job["payload"] == {"k": 1}
    jobqueue.complete(db_det, jid)
    db_det.commit()
    cur = db_superuser.cursor()
    cur.execute("SELECT status, worker_id FROM pipeline_jobs WHERE id=%s", (jid,))
    assert cur.fetchone() == ("completed", "worker-t")


def test_skip_locked_two_workers_get_different_jobs(db_superuser, clean_jobs):
    app_id = clean_jobs
    c0 = _connect("app_det")
    ids = [jobqueue.enqueue(c0, app_id, "EXTRACT", priority=20_000 + i) for i in range(2)]
    c0.commit()
    c1, c2 = _connect("app_det"), _connect("app_det")
    try:
        j1 = jobqueue.dequeue(c1, "w1")  # c1 holds its row lock (txn open)
        j2 = jobqueue.dequeue(c2, "w2")  # must skip the locked row
        assert j1 and j2 and j1["id"] != j2["id"]
        assert {j1["id"], j2["id"]} == set(ids)
        c1.commit()
        c2.commit()
    finally:
        for c in (c0, c1, c2):
            c.close()


def test_scheduled_in_future_not_dequeued(db_det, clean_jobs):
    app_id = clean_jobs
    jid = jobqueue.enqueue(db_det, app_id, "VERIFY", priority=30_000, delay_s=3600)
    db_det.commit()
    job = jobqueue.dequeue(db_det, "w")
    db_det.commit()
    assert job is None or job["id"] != jid


def test_failed_job_records_error(db_det, db_superuser, clean_jobs):
    app_id = clean_jobs
    jid = jobqueue.enqueue(db_det, app_id, "RULES", priority=40_000)
    db_det.commit()
    job = jobqueue.dequeue(db_det, "w")
    assert job["id"] == jid
    jobqueue.fail(db_det, jid, "boom")
    db_det.commit()
    cur = db_superuser.cursor()
    cur.execute("SELECT status, error FROM pipeline_jobs WHERE id=%s", (jid,))
    assert cur.fetchone() == ("failed", "boom")
