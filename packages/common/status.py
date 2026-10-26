"""Status enums matching the six PS-defined verification statuses."""
from __future__ import annotations

from enum import Enum


class VerificationStatus(str, Enum):
    """The six statuses from the PS document."""
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class DocumentStatus(str, Enum):
    """High-level document processing status."""
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    UNREADABLE = "UNREADABLE"


class ApplicationStage(str, Enum):
    """Pipeline stages for an application."""
    SUBMITTED = "SUBMITTED"
    INGESTING = "INGESTING"
    PARSING = "PARSING"
    EXTRACTING = "EXTRACTING"
    CLASSIFYING = "CLASSIFYING"
    RULES = "RULES"
    VERIFYING = "VERIFYING"
    DETECTING = "DETECTING"
    LINKING = "LINKING"
    DIAGNOSING = "DIAGNOSING"
    ROUTING = "ROUTING"
    REPORTING = "REPORTING"
    ALERTING = "ALERTING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ReviewLevel(int, Enum):
    """Escalation levels."""
    LEVEL_0 = 0  # Low-risk, sampled
    LEVEL_1 = 1  # Standard scrutiny officer
    LEVEL_2 = 2  # Supervisor
    LEVEL_3 = 3  # Competent authority (inspection)


class SystemMode(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"


class FindingResult(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ClaimState(str, Enum):
    PROVEN = "PROVEN"
    REFUTED = "REFUTED"
    UNPROVEN = "UNPROVEN"
    CONFLICTING = "CONFLICTING"


class InformationRequestState(str, Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    CLOSED = "CLOSED"
    OVERDUE = "OVERDUE"


class UserRole(str, Enum):
    INSTITUTION_USER = "institution_user"
    SCRUTINY_OFFICER = "scrutiny_officer"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"
    RULES_ADMIN = "rules_admin"
    SYSADMIN = "sysadmin"
