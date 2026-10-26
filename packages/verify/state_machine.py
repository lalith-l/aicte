"""Verification state machine and retry backoff schedule.

Retry schedule for SOURCE_UNAVAILABLE:
- Attempt 1: 1 minute (60s)
- Attempt 2: 4 minutes (240s)
- Attempt 3: 15 minutes (900s)
- Attempt 4+: Daily (86400s) up to 7 attempts

Authority rule:
Only deterministic code (app_det) and humans can write a status or finding.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import datetime
from typing import Optional
from packages.verify.connectors import VerificationStatus

RETRY_SCHEDULE_SECONDS = [60, 240, 900, 86400, 86400, 86400, 86400]


def get_next_retry_time(attempt_number: int, current_time: Optional[datetime.datetime] = None) -> Optional[datetime.datetime]:
    """Calculate timestamp for next retry attempt."""
    if attempt_number >= len(RETRY_SCHEDULE_SECONDS):
        return None  # Exceeded retry budget
    
    now = current_time or datetime.datetime.now(datetime.timezone.utc)
    delay_s = RETRY_SCHEDULE_SECONDS[attempt_number]
    return now + datetime.timedelta(seconds=delay_s)


def can_transition(current: VerificationStatus, new_status: VerificationStatus) -> bool:
    """Validate verification status transition."""
    if current == VerificationStatus.VERIFIED:
        # Final state unless revocation occurs
        return new_status in (VerificationStatus.VERIFIED, VerificationStatus.FAILED_VERIFICATION)
    
    if current == VerificationStatus.SOURCE_UNAVAILABLE:
        # Transient state, can transition to any upon retry
        return True

    if current == VerificationStatus.CONSENT_REQUIRED:
        # Can transition once token is supplied or timeout
        return new_status in (VerificationStatus.VERIFIED, VerificationStatus.FAILED_VERIFICATION, VerificationStatus.SOURCE_UNAVAILABLE)

    return True
