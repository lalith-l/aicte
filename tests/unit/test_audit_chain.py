"""GATE TEST: Audit chain integrity.

Tests:
1. Chain of 100 entries verifies correctly
2. Tampering one entry breaks verification at that seq
3. Recomputing all hashes after tampering passes internal check but fails against published head
"""
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.common.hashing import compute_chain_hash, verify_chain, canonical_json
from datetime import datetime, timezone


pytestmark = pytest.mark.gate


def _build_chain(n: int) -> list[dict]:
    """Build a chain of n audit entries."""
    chain = []
    prev_hash = ""
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

    for i in range(1, n + 1):
        ts = base_time.replace(second=i % 60, minute=i // 60)
        actor = f"user_{i % 5}"
        action = f"action_{i % 3}"
        payload = {"application_id": f"app-{i}", "rule_code": f"R-{i:03d}"}

        h = compute_chain_hash(prev_hash, i, ts, actor, action, payload)
        chain.append({
            "seq": i,
            "ts": ts,
            "actor": actor,
            "action": action,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": h,
        })
        prev_hash = h

    return chain


class TestAuditChainIntegrity:

    def test_valid_chain_passes(self):
        """A correctly built chain of 100 entries verifies."""
        chain = _build_chain(100)
        valid, broken_seq = verify_chain(chain)
        assert valid is True
        assert broken_seq is None

    def test_tampered_entry_detected(self):
        """Changing one payload breaks the chain at that seq."""
        chain = _build_chain(100)

        # Tamper entry 50's payload
        chain[49]["payload"]["application_id"] = "TAMPERED"

        valid, broken_seq = verify_chain(chain)
        assert valid is False
        assert broken_seq == 50

    def test_tampered_first_entry(self):
        """Tampering the first entry is detected."""
        chain = _build_chain(10)
        chain[0]["payload"]["rule_code"] = "HACKED"

        valid, broken_seq = verify_chain(chain)
        assert valid is False
        assert broken_seq == 1

    def test_recomputed_chain_vs_published_head(self):
        """After tampering, an attacker recomputes all later hashes.
        Internal verification passes, but the published head hash no longer matches."""
        chain = _build_chain(50)

        # Save the published head hash (what was emailed/published)
        published_head = chain[-1]["hash"]

        # Tamper entry 25 and recompute everything after it
        chain[24]["payload"]["application_id"] = "FORGED"
        # Recompute hash for entry 25
        chain[24]["hash"] = compute_chain_hash(
            chain[24]["prev_hash"], chain[24]["seq"], chain[24]["ts"],
            chain[24]["actor"], chain[24]["action"], chain[24]["payload"]
        )
        # Recompute all subsequent entries
        for i in range(25, len(chain)):
            chain[i]["prev_hash"] = chain[i - 1]["hash"]
            chain[i]["hash"] = compute_chain_hash(
                chain[i]["prev_hash"], chain[i]["seq"], chain[i]["ts"],
                chain[i]["actor"], chain[i]["action"], chain[i]["payload"]
            )

        # Internal verification now passes (chain is self-consistent)
        valid, broken_seq = verify_chain(chain)
        assert valid is True, "Recomputed chain should be internally consistent"

        # BUT the published head hash no longer matches
        new_head = chain[-1]["hash"]
        assert new_head != published_head, (
            "The recomputed chain's head must differ from the published head"
        )

    def test_empty_chain(self):
        """Empty chain is valid."""
        valid, broken_seq = verify_chain([])
        assert valid is True
        assert broken_seq is None

    def test_single_entry(self):
        """Single-entry chain verifies."""
        chain = _build_chain(1)
        valid, broken_seq = verify_chain(chain)
        assert valid is True


class TestCanonicalJson:
    def test_sorted_keys(self):
        """Keys are sorted."""
        result = canonical_json({"b": 1, "a": 2})
        assert result == b'{"a":2,"b":1}'

    def test_no_spaces(self):
        """No whitespace in output."""
        result = canonical_json({"key": "value"})
        assert b" " not in result

    def test_deterministic(self):
        """Same input always produces same output."""
        d = {"action": "test", "seq": 1, "payload": {"x": "y"}}
        assert canonical_json(d) == canonical_json(d)
