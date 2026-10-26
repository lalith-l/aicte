"""Postgres job queue (FOR UPDATE SKIP LOCKED). No Redis."""

from __future__ import annotations

import json
from typing import Any, Optional

STAGES = [
    "INGEST",
    "PARSE",
    "EXTRACT",
    "RULES",
    "VERIFY",
    "DETECT",
    "DIAGNOSE",
    "ROUTE",
    "REPORT",
    "ALERT",
]


def enqueue(
    conn,
    application_id: str,
    stage: str,
    payload: Optional[dict] = None,
    priority: int = 0,
    delay_s: int = 0,
) -> str:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO pipeline_jobs (application_id, stage, payload, priority, scheduled_at) "
        "VALUES (%s, %s, %s::jsonb, %s, NOW() + make_interval(secs => %s)) RETURNING id",
        (application_id, stage, json.dumps(payload or {}), priority, delay_s),
    )
    job_id = str(cur.fetchone()[0])
    cur.close()
    return job_id


def dequeue(conn, worker_id: str) -> Optional[dict[str, Any]]:
    """Claim the next due job. Concurrent workers never receive the same job."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE pipeline_jobs SET status='running', started_at=NOW(), worker_id=%s
        WHERE id = (
            SELECT id FROM pipeline_jobs
            WHERE status='pending' AND scheduled_at <= NOW()
            ORDER BY priority DESC, created_at ASC
            LIMIT 1 FOR UPDATE SKIP LOCKED
        )
        RETURNING id, application_id, stage, payload
        """,
        (worker_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        conn.commit()
        return None
    conn.commit()
    return {
        "id": str(row[0]),
        "application_id": str(row[1]),
        "stage": row[2],
        "payload": row[3] or {},
    }


def complete(conn, job_id: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE pipeline_jobs SET status='completed', completed_at=NOW() WHERE id=%s", (job_id,)
    )
    cur.close()


def fail(conn, job_id: str, error: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE pipeline_jobs SET status='failed', completed_at=NOW(), error=%s WHERE id=%s",
        (error[:2000], job_id),
    )
    cur.close()
