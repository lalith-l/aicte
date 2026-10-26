"""Audit chain hashing: SHA-256 chain with canonical JSON.

The chain is append-only. Each entry stores:
    hash = SHA256(prev_hash || canonical_json(seq, ts, actor, action, payload))

Canonical JSON: sorted keys, no spaces, UTF-8.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    """Produce canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compute_chain_hash(
    prev_hash: str,
    seq: int,
    ts: datetime,
    actor: str,
    action: str,
    payload: dict[str, Any],
) -> str:
    """Compute hash = SHA256(prev_hash || canonical_json({seq, ts, actor, action, payload})).

    The timestamp is ISO 8601 UTC with microseconds.
    """
    entry = {
        "seq": seq,
        "ts": ts.astimezone(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "payload": payload,
    }
    message = prev_hash.encode("utf-8") + canonical_json(entry)
    return hashlib.sha256(message).hexdigest()


def verify_chain(entries: list[dict[str, Any]]) -> tuple[bool, int | None]:
    """Verify the entire audit chain.

    Returns (True, None) if valid, or (False, seq) where seq is the first broken entry.
    Entries must be sorted by seq ascending and include:
        seq, ts (datetime), actor, action, payload, prev_hash, hash
    """
    for entry in entries:
        expected = compute_chain_hash(
            prev_hash=entry["prev_hash"],
            seq=entry["seq"],
            ts=entry["ts"],
            actor=entry["actor"],
            action=entry["action"],
            payload=entry["payload"],
        )
        if expected != entry["hash"]:
            return False, entry["seq"]
    return True, None
