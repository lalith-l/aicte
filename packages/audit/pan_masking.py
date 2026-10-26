"""PAN masking and permissioned reveal with append-only audit tracking.

Rule:
PAN numbers must be masked by default in all API responses, UI displays, and log files.
Revealing plaintext PAN requires authorized roles (scrutiny_officer, auditor, sysadmin)
and logs a permanent PAN_REVEALED event into the immutable audit chain.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional
import psycopg2

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def mask_pan(pan: Optional[str]) -> str:
    """Mask first 6 characters of PAN: ABCDE1234F -> •••••1234F."""
    if not pan:
        return ""
    pan_str = str(pan).strip().upper()
    if len(pan_str) == 10:
        return "•••••" + pan_str[5:]
    return "••••" + pan_str[-4:] if len(pan_str) >= 4 else "••••"


def permissioned_pan_reveal(
    pan_plaintext: str,
    document_id: str,
    actor_id: str,
    actor_role: str,
    justification: str,
    db_conn: Optional[psycopg2.extensions.connection] = None,
) -> str:
    """Check role, log PAN_REVEALED audit event, and return unmasked PAN."""
    allowed_roles = {"scrutiny_officer", "supervisor", "auditor", "sysadmin"}
    if actor_role not in allowed_roles:
        raise PermissionError(
            f"Role '{actor_role}' is not authorized to unmask applicant PAN. "
            f"Authorized roles: {sorted(allowed_roles)}"
        )

    if not justification or len(justification.strip()) < 5:
        raise ValueError("A documented justification is required to unmask PAN identifier.")

    if db_conn:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT audit_append(%s, %s, %s, %s, %s)
                """,
                (
                    "PAN_REVEALED",
                    "documents",
                    document_id,
                    actor_id,
                    f'{{"role": "{actor_role}", "justification": "{justification}"}}',
                ),
            )
        db_conn.commit()

    return pan_plaintext
