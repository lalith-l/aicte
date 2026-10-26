"""Database role constants.

These match the PostgreSQL roles created by the schema setup script.
Each pipeline stage connects with its own role, so a model worker
physically cannot write a status.
"""
from __future__ import annotations

# Roles
ROLE_API = "app_api"           # API requests: institution users, officers
ROLE_DET = "app_det"           # Deterministic writer: rules, verification, Tier 1 detectors
ROLE_MODEL = "app_model"       # Model writer: indicators, risk scores
ROLE_MONITOR = "app_monitor"   # Canary monitor: reads sealed schema
ROLE_MIGRATOR = "migrator"     # Schema migrations only
ROLE_READONLY = "app_readonly" # Read-only (auditor queries)

# Tables that are INSERT-ONLY (no UPDATE, no DELETE for any role)
APPEND_ONLY_TABLES = [
    "audit_log",
    "findings",
    "document_status",
    "verification_results",
    "indicators",
    "risk_scores",
    "reviewer_actions",  # correction #5: reviewer_actions is insert-only
]

# Tables where INSERT is restricted by role
DET_ONLY_INSERT = ["findings", "document_status", "verification_results"]
MODEL_ONLY_INSERT = ["indicators", "risk_scores"]

# Tables that allow DELETE (for crypto-shredding)
DELETABLE_TABLES = ["file_keys"]
