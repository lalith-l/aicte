"""External head-hash publisher and tamper detection.

Published daily to data/mail/head_hash_{date}.json.
Guarantees that even if an attacker tampers with an audit row AND recomputes
all subsequent hashes in the database, the discrepancy is immediately caught
against the published head hash.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Optional, Tuple

import psycopg2

EXTERNAL_HEAD_DIR = Path("/Users/lalithkumargn/Desktop/aicte/data/mail")
EXTERNAL_HEAD_DIR.mkdir(parents=True, exist_ok=True)


def publish_head_hash(
    db_conn: psycopg2.extensions.connection,
    published_by: str = "daily_cron",
    date_str: Optional[str] = None,
) -> dict:
    """Fetch head hash from audit_log and write to external mail/head_hash_{date}.json."""
    if not date_str:
        date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT seq, hash, ts, action, actor
            FROM audit_log
            ORDER BY seq DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if not row:
        record = {
            "date": date_str,
            "seq": 0,
            "head_hash": "GENESIS_EMPTY",
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "published_by": published_by,
            "synthetic": True,
        }
    else:
        seq, head_hash, ts, action, actor = row
        record = {
            "date": date_str,
            "seq": seq,
            "head_hash": head_hash,
            "action": action,
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "published_by": published_by,
            "synthetic": True,
        }

    out_file = EXTERNAL_HEAD_DIR / f"head_hash_{date_str}.json"
    with open(out_file, "w") as f:
        json.dump(record, f, indent=2)

    return record


def verify_against_external_head(
    db_conn: psycopg2.extensions.connection,
    date_str: str,
) -> Tuple[bool, str]:
    """Verify that the database audit chain matches the externally published head hash."""
    head_file = EXTERNAL_HEAD_DIR / f"head_hash_{date_str}.json"
    if not head_file.exists():
        return False, f"External published head file for date {date_str} not found"

    with open(head_file, "r") as f:
        external_record = json.load(f)

    target_seq = external_record["seq"]
    expected_hash = external_record["head_hash"]

    if target_seq == 0 and expected_hash == "GENESIS_EMPTY":
        return True, "Chain was empty at publication time"

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT hash FROM audit_log WHERE seq = %s
            """,
            (target_seq,),
        )
        row = cur.fetchone()

    if not row:
        return False, f"Database does not contain sequence {target_seq} recorded in external head"

    db_hash = row[0]
    if db_hash != expected_hash:
        return False, (
            f"TAMPER DETECTED: Database hash at seq {target_seq} ({db_hash}) "
            f"does not match externally published head hash ({expected_hash})"
        )

    return True, f"Verified: Head hash at seq {target_seq} matches external publication"
