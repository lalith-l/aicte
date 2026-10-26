"""Audit chain verification + external head-hash publication.

The chain is verified by `audit_verify()` inside Postgres (it recomputes with the exact
expression used by `audit_append()`). Verifying only against the DB is not enough: someone
with superuser rights can edit a row and recompute every later hash, producing a chain that
verifies internally. The *published head hash* — written daily outside the database to
`data/mail/head_hash_{date}.json` — catches that, because the recomputed chain no longer
contains the hash that was published.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from packages.common.paths import MAIL_DIR


@dataclass
class ChainStatus:
    ok: bool
    broken_seq: Optional[int]
    entries: int
    head_seq: Optional[int]
    head_hash: str


@dataclass
class PublishedHeadCheck:
    ok: bool
    date: str
    published_seq: int
    published_hash: str
    current_hash_at_seq: Optional[str]
    message: str


def verify_chain_db(conn) -> ChainStatus:
    cur = conn.cursor()
    cur.execute("SELECT ok, broken_seq, entries, head_seq, head_hash FROM audit_verify()")
    ok, broken, entries, head_seq, head_hash = cur.fetchone()
    cur.close()
    return ChainStatus(bool(ok), broken, int(entries), head_seq, head_hash or "")


def _head(conn) -> tuple[int, str, int]:
    cur = conn.cursor()
    cur.execute("SELECT head_seq, head_hash, entries FROM audit_head()")
    row = cur.fetchone()
    cur.close()
    return int(row[0]), row[1], int(row[2])


def publish_head(conn, day: Optional[date] = None, out_dir: Path = MAIL_DIR) -> Path:
    """Write today's head hash outside the database. Idempotent per day (one file/day,
    never overwritten: the first publication of a day is the one that counts)."""
    day = day or datetime.now(timezone.utc).date()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"head_hash_{day.isoformat()}.json"
    if path.exists():
        return path
    seq, h, n = _head(conn)
    path.write_text(
        json.dumps(
            {
                "date": day.isoformat(),
                "head_seq": seq,
                "head_hash": h,
                "entry_count": n,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "synthetic_data": True,
            },
            indent=2,
        )
    )
    return path


def list_published_heads(out_dir: Path = MAIL_DIR) -> list[dict]:
    heads = []
    for p in sorted(out_dir.glob("head_hash_*.json")):
        try:
            heads.append(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return heads


def check_published_head(conn, published: dict) -> PublishedHeadCheck:
    """Does the chain still contain the exact hash that was published for that seq?"""
    cur = conn.cursor()
    cur.execute("SELECT hash FROM audit_log WHERE seq=%s", (published["head_seq"],))
    row = cur.fetchone()
    cur.close()
    current = row[0] if row else None
    ok = current == published["head_hash"]
    msg = (
        "matches published head"
        if ok
        else f"MISMATCH at seq {published['head_seq']}: chain was rewritten after publication"
        if current
        else f"seq {published['head_seq']} no longer exists in the chain"
    )
    return PublishedHeadCheck(
        ok, published["date"], published["head_seq"], published["head_hash"], current, msg
    )


def full_report(conn, out_dir: Path = MAIL_DIR) -> dict:
    """Internal verification + every published head. Used by the auditor view and CLI."""
    internal = verify_chain_db(conn)
    checks = [asdict(check_published_head(conn, h)) for h in list_published_heads(out_dir)]
    return {
        "internal": asdict(internal),
        "published": checks,
        "all_ok": internal.ok and all(c["ok"] for c in checks),
    }
