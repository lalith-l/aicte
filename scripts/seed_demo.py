"""Seed the database with demo users and the Sunrise Institute application.

Usage: python scripts/seed_demo.py

Creates:
- 6 users (one per role) with password 'demo123'
- Sunrise Institute with a seeded application containing 2-3 known defects
- All data is synthetic

PLACEHOLDER: All clause references, handbook numbers, and minimum values
must be filled by a person. Do not generate them.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.api.app.auth.routes import hash_password

DB_NAME = os.environ.get("AICTE_DB_NAME", "aicte_validator")
PG_BIN = os.environ.get("PG_BIN", "/opt/homebrew/opt/postgresql@16/bin")
PW_HASH = hash_password("demo123")

SEED_SQL = f"""
-- ============================================================
-- Sunrise Institute (seeded for demo)
-- ============================================================
INSERT INTO institutions (id, name, code, address, city, state, pin_code)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Sunrise Technical Institute',
    'SUNRISE-001',
    '123 Academic Road, Tech Park',
    'Bengaluru',
    'Karnataka',
    '560001'
) ON CONFLICT (code) DO NOTHING;

-- Additional institutions
INSERT INTO institutions (id, name, code, address, city, state, pin_code) VALUES
    ('22222222-2222-2222-2222-222222222222', 'Horizon Engineering College', 'HORIZON-001', '456 University Ave', 'Chennai', 'Tamil Nadu', '600001'),
    ('33333333-3333-3333-3333-333333333333', 'Pinnacle College of Science', 'PINNACLE-001', '789 Knowledge Park', 'Hyderabad', 'Telangana', '500001'),
    ('44444444-4444-4444-4444-444444444444', 'Greenfield Institute of Technology', 'GIT-001', '101 Metro Way', 'Pune', 'Maharashtra', '411001'),
    ('55555555-5555-5555-5555-555555555555', 'Westland Engineering College', 'WEC-001', '202 Ring Road', 'Ahmedabad', 'Gujarat', '380001'),
    ('66666666-6666-6666-6666-666666666666', 'Rajendra Institute of Management', 'RIM-001', '303 Palace Road', 'Jaipur', 'Rajasthan', '302001'),
    ('77777777-7777-7777-7777-777777777777', 'Northstar Academy of Sciences', 'NAS-001', '404 Salt Lake', 'Kolkata', 'West Bengal', '700001'),
    ('88888888-8888-8888-8888-888888888888', 'Eastern Polytechnic Institute', 'EPI-001', '505 Infocity', 'Bhubaneswar', 'Odisha', '751001')
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- Demo Users (password: demo123 for all)
-- ============================================================
INSERT INTO users (id, username, email, pw_hash, role, institution_id) VALUES
    ('aaaa0001-0001-0001-0001-000000000001', 'sunrise_admin', 'admin@sunrise.edu', '{PW_HASH}', 'institution_user', '11111111-1111-1111-1111-111111111111'),
    ('aaaa0002-0002-0002-0002-000000000002', 'officer_raj', 'raj@aicte.gov', '{PW_HASH}', 'scrutiny_officer', NULL),
    ('aaaa0003-0003-0003-0003-000000000003', 'supervisor_priya', 'priya@aicte.gov', '{PW_HASH}', 'supervisor', NULL),
    ('aaaa0004-0004-0004-0004-000000000004', 'auditor_amit', 'amit@aicte.gov', '{PW_HASH}', 'auditor', NULL),
    ('aaaa0005-0005-0005-0005-000000000005', 'rules_meera', 'meera@aicte.gov', '{PW_HASH}', 'rules_admin', NULL),
    ('aaaa0006-0006-0006-0006-000000000006', 'sysadmin_dev', 'dev@aicte.gov', '{PW_HASH}', 'sysadmin', NULL),
    ('aaaa0007-0007-0007-0007-000000000007', 'horizon_admin', 'admin@horizon.edu', '{PW_HASH}', 'institution_user', '22222222-2222-2222-2222-222222222222')
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- Sunrise Application (seeded with known defects for demo)
-- ============================================================
INSERT INTO applications (id, institution_id, declared_category, academic_year, stage)
VALUES
    ('bbbb0001-0001-0001-0001-000000000001', '11111111-1111-1111-1111-111111111111', 'EOA Renewal', '2025-26', 'UNDER_REVIEW'),
    ('bbbb0002-0002-0002-0002-000000000002', '22222222-2222-2222-2222-222222222222', 'New Approval', '2025-26', 'SUBMITTED'),
    ('bbbb0003-0003-0003-0003-000000000003', '33333333-3333-3333-3333-333333333333', 'EOA Renewal', '2025-26', 'DECISION_PENDING'),
    ('bbbb0004-0004-0004-0004-000000000004', '44444444-4444-4444-4444-444444444444', 'Intake Enhancement', '2025-26', 'APPROVED'),
    ('bbbb0005-0005-0005-0005-000000000005', '55555555-5555-5555-5555-555555555555', 'EOA Renewal', '2025-26', 'REJECTED'),
    ('bbbb0006-0006-0006-0006-000000000006', '66666666-6666-6666-6666-666666666666', 'New Approval', '2025-26', 'EXTRACTING'),
    ('bbbb0007-0007-0007-0007-000000000007', '77777777-7777-7777-7777-777777777777', 'EOA Renewal', '2025-26', 'UNDER_REVIEW'),
    ('bbbb0008-0008-0008-0008-000000000008', '88888888-8888-8888-8888-888888888888', 'Intake Enhancement', '2025-26', 'INGESTING')
ON CONFLICT DO NOTHING;

-- Documents for Sunrise application
INSERT INTO documents (id, application_id, type_declared, file_ref, sha256, page_count) VALUES
    ('cccc0001-0001-0001-0001-000000000001', 'bbbb0001-0001-0001-0001-000000000001', 'trust_deed', 'sunrise/trust_deed.pdf', 'a1b2c3d4e5f6', 3),
    ('cccc0002-0002-0002-0002-000000000002', 'bbbb0001-0001-0001-0001-000000000001', 'affidavit', 'sunrise/affidavit.pdf', 'b2c3d4e5f6a1', 2),
    ('cccc0003-0003-0003-0003-000000000003', 'bbbb0001-0001-0001-0001-000000000001', 'stamp_paper', 'sunrise/stamp_paper.pdf', 'c3d4e5f6a1b2', 1),
    ('cccc0004-0004-0004-0004-000000000004', 'bbbb0001-0001-0001-0001-000000000001', 'faculty_list', 'sunrise/faculty_list.pdf', 'd4e5f6a1b2c3', 5),
    ('cccc0005-0005-0005-0005-000000000005', 'bbbb0001-0001-0001-0001-000000000001', 'noc', 'sunrise/noc_certificate.pdf', 'e5f6a1b2c3d4', 1)
ON CONFLICT DO NOTHING;

-- Seeded extracted fields (static data for early Dossier rendering)
INSERT INTO extracted_fields (document_id, field, value, normalized, page, confidence, extractor, agree) VALUES
    ('cccc0001-0001-0001-0001-000000000001', 'institution_name', 'Sunrise Technical Institute', 'sunrise technical institute', 1, 0.98, 'pdfplumber', true),
    ('cccc0001-0001-0001-0001-000000000001', 'trust_name', 'Sunrise Education Trust', 'sunrise education trust', 1, 0.96, 'pdfplumber', true),
    ('cccc0002-0002-0002-0002-000000000002', 'affidavit_date', '2025-01-15', '2025-01-15', 1, 0.95, 'pdfplumber', true),
    ('cccc0002-0002-0002-0002-000000000002', 'signatory_name', 'Dr. R. Kumar', 'dr r kumar', 1, 0.93, 'pdfplumber', true),
    ('cccc0001-0001-0001-0001-000000000001', 'pan_number', 'AAACT1234A', 'aaact1234a', 1, 0.90, 'pdfplumber', true),
    ('cccc0003-0003-0003-0003-000000000003', 'stamp_paper_date', '2025-02-01', '2025-02-01', 1, 0.97, 'pdfplumber', true),
    ('cccc0003-0003-0003-0003-000000000003', 'stamp_paper_value', '500', '500', 1, 0.99, 'pdfplumber', true),
    ('cccc0004-0004-0004-0004-000000000004', 'faculty_count', '42', '42', 1, 0.91, 'pdfplumber', true),
    ('cccc0005-0005-0005-0005-000000000005', 'noc_issuer', 'State Government of Karnataka', 'state government of karnataka', 1, 0.94, 'pdfplumber', true),
    ('cccc0005-0005-0005-0005-000000000005', 'noc_date', '2025-02-10', '2025-02-10', 1, 0.96, 'pdfplumber', true)
ON CONFLICT DO NOTHING;

-- ============================================================
-- Seeded Findings (known defects for Sunrise — demo beat 1 & 2)
-- ============================================================

-- D04: Affidavit date conflicts with stamp paper date
-- PLACEHOLDER: clause_ref must come from the real handbook
INSERT INTO findings (id, application_id, source_code, tier, result, reason, evidence, recheck_recipe) VALUES
    ('dddd0001-0001-0001-0001-000000000001',
     'bbbb0001-0001-0001-0001-000000000001',
     'D04-date-inconsistency',
     1,
     'FALSE',
     'Affidavit date (2025-01-15) conflicts with stamp paper date (2025-02-01). Stamp paper was purchased after the affidavit was executed.',
     '{{"documents": ["cccc0002-0002-0002-0002-000000000002", "cccc0003-0003-0003-0003-000000000003"], "fields": ["affidavit_date", "stamp_paper_date"], "bounding_boxes": [{{"doc_id": "cccc0002-0002-0002-0002-000000000002", "page": 1, "x": 120, "y": 340, "w": 200, "h": 25}}, {{"doc_id": "cccc0003-0003-0003-0003-000000000003", "page": 1, "x": 80, "y": 150, "w": 180, "h": 20}}]}}',
     'Compare affidavit date with stamp paper date. Verify stamp paper was purchased before affidavit execution.')
ON CONFLICT DO NOTHING;

-- D13: Source unavailable (issuer unreachable)
INSERT INTO findings (id, application_id, source_code, tier, result, reason, evidence) VALUES
    ('dddd0002-0002-0002-0002-000000000002',
     'bbbb0001-0001-0001-0001-000000000001',
     'D13-source-unavailable',
     2,
     'UNKNOWN',
     'NOC issuer verification endpoint returned 503. Verification debt increased. No rejection — UNKNOWN is not FALSE.',
     '{{"documents": ["cccc0005-0005-0005-0005-000000000005"], "status": "SOURCE_UNAVAILABLE", "last_attempt": "2025-03-15T10:30:00Z"}}')
ON CONFLICT DO NOTHING;

-- Seeded document statuses
INSERT INTO document_status (document_id, status, source) VALUES
    ('cccc0001-0001-0001-0001-000000000001', 'VERIFIED', 'signature_check'),
    ('cccc0002-0002-0002-0002-000000000002', 'VERIFIED', 'signature_check'),
    ('cccc0003-0003-0003-0003-000000000003', 'VERIFIED', 'signature_check'),
    ('cccc0004-0004-0004-0004-000000000004', 'MANUAL_REVIEW_REQUIRED', 'extraction_disagreement'),
    ('cccc0005-0005-0005-0005-000000000005', 'SOURCE_UNAVAILABLE', 'issuer_503')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Seeded Diagnosis (basic, correction #3 — static for now)
-- Label: "seeded static diagnosis, not computed"
-- ============================================================
-- The diagnosis identifies which single document to verify first
-- to resolve the most findings. This is a static placeholder.
-- When the real diagnosis engine (hitting-set) is built, it will
-- replace this with computed results.

-- Using reviewer_notes as a lightweight carrier for the seeded diagnosis
INSERT INTO reviewer_notes (application_id, note_text, note_hash, user_id) VALUES
    ('bbbb0001-0001-0001-0001-000000000001',
     '{{\"type\": \"seeded_diagnosis\", \"label\": \"seeded static diagnosis, not computed\", \"recommendation\": \"Verify NOC certificate (cccc0005) first — resolves D13 (SOURCE_UNAVAILABLE) and may affect D04 cross-check.\", \"priority_document\": \"cccc0005-0005-0005-0005-000000000005\", \"findings_affected\": [\"dddd0002-0002-0002-0002-000000000002\"]}}',
     'static-seed-hash',
     'aaaa0006-0006-0006-0006-000000000006')
ON CONFLICT DO NOTHING;

-- ============================================================
-- Audit trail: covers PS list events end-to-end for one application
-- ============================================================
SELECT audit_append('system', 'seed_demo', '{{"action": "database_seeded", "sunrise_application": "bbbb0001-0001-0001-0001-000000000001", "synthetic_data": true}}'::jsonb);
SELECT audit_append('system', 'seed_demo', '{{"action": "demo_users_created", "user_count": 7, "synthetic_data": true}}'::jsonb);
SELECT audit_append('system', 'ingest_gate', '{{"action": "document_ingested", "application_id": "bbbb0001-0001-0001-0001-000000000001", "document_id": "cccc0001-0001-0001-0001-000000000001", "type": "trust_deed", "sha256_ok": true}}'::jsonb);
SELECT audit_append('system', 'ingest_gate', '{{"action": "document_ingested", "application_id": "bbbb0001-0001-0001-0001-000000000001", "document_id": "cccc0002-0002-0002-0002-000000000002", "type": "affidavit", "sha256_ok": true}}'::jsonb);
SELECT audit_append('system', 'ingest_gate', '{{"action": "document_ingested", "application_id": "bbbb0001-0001-0001-0001-000000000001", "document_id": "cccc0003-0003-0003-0003-000000000003", "type": "stamp_paper", "sha256_ok": true}}'::jsonb);
SELECT audit_append('system', 'extractor', '{{"action": "extraction_complete", "application_id": "bbbb0001-0001-0001-0001-000000000001", "document_id": "cccc0002-0002-0002-0002-000000000002", "fields_extracted": ["affidavit_date", "signatory_name"], "extractor": "pdfplumber"}}'::jsonb);
SELECT audit_append('system', 'extractor', '{{"action": "extraction_complete", "application_id": "bbbb0001-0001-0001-0001-000000000001", "document_id": "cccc0003-0003-0003-0003-000000000003", "fields_extracted": ["stamp_paper_date", "stamp_paper_value"], "extractor": "pdfplumber"}}'::jsonb);
SELECT audit_append('system', 'rules_engine', '{{"action": "rule_applied", "application_id": "bbbb0001-0001-0001-0001-000000000001", "rule_id": "R-D04", "result": "FALSE", "reason": "affidavit_date < stamp_paper_date", "clause_ref": "PLACEHOLDER"}}'::jsonb);
SELECT audit_append('system', 'rules_engine', '{{"action": "rule_applied", "application_id": "bbbb0001-0001-0001-0001-000000000001", "rule_id": "R-D13", "result": "UNKNOWN", "reason": "issuer_endpoint_503", "clause_ref": "PLACEHOLDER"}}'::jsonb);
SELECT audit_append('system', 'issuer_connector', '{{"action": "source_queried", "application_id": "bbbb0001-0001-0001-0001-000000000001", "issuer": "State Government of Karnataka", "route": "reference_lookup", "http_status": 503, "result": "SOURCE_UNAVAILABLE"}}'::jsonb);
SELECT audit_append('system', 'alert_engine', '{{"action": "alert_raised", "application_id": "bbbb0001-0001-0001-0001-000000000001", "alert_type": "SOURCE_OUTAGE", "severity": "medium", "message": "NOC issuer 503"}}'::jsonb);
SELECT audit_append('system', 'alert_engine', '{{"action": "alert_raised", "application_id": "bbbb0001-0001-0001-0001-000000000001", "alert_type": "FINDING_RAISED", "severity": "high", "message": "D04 date inconsistency"}}'::jsonb);
SELECT audit_append('officer_raj', 'review_assigned', '{{"action": "review_assigned", "application_id": "bbbb0001-0001-0001-0001-000000000001", "review_item_id": "eeee0001-0001-0001-0001-000000000001", "level": 2}}'::jsonb);
SELECT audit_append('officer_raj', 'pii_reveal', '{{"action": "pii_reveal", "application_id": "bbbb0001-0001-0001-0001-000000000001", "field": "pan_number", "masked_value": "AAAC****4A", "purpose": "identity_verification"}}'::jsonb);
SELECT audit_append('officer_raj', 'observation_recorded', '{{"action": "observation_recorded", "application_id": "bbbb0001-0001-0001-0001-000000000001", "finding_id": "dddd0001-0001-0001-0001-000000000001", "observation": "Date conflict confirmed on physical review"}}'::jsonb);
SELECT audit_append('system', 'portal_record_checked', '{{"action": "portal_record_checked", "application_id": "bbbb0001-0001-0001-0001-000000000001", "portal": "AICTE_PORTAL", "institution_code": "SUNRISE-001", "match": true}}'::jsonb);

INSERT INTO review_items (id, application_id, level, reason, assignee, state) VALUES
    ('eeee0001-0001-0001-0001-000000000001', 'bbbb0001-0001-0001-0001-000000000001', 2, 'Sunrise D04+D13', 'aaaa0002-0002-0002-0002-000000000002', 'assigned')
ON CONFLICT DO NOTHING;

INSERT INTO risk_scores (application_id, score, model_version) VALUES
    ('bbbb0001-0001-0001-0001-000000000001', 0.73, 'seed-static')
ON CONFLICT DO NOTHING;

UPDATE applications SET stage = 'UNDER_REVIEW'
 WHERE id = 'bbbb0001-0001-0001-0001-000000000001';

INSERT INTO alerts (type, application_id, message, severity) VALUES
    ('FINDING_RAISED', 'bbbb0001-0001-0001-0001-000000000001', 'D04 date inconsistency on Sunrise affidavit vs stamp paper', 'high'),
    ('SOURCE_OUTAGE', 'bbbb0001-0001-0001-0001-000000000001', 'NOC issuer 503 — verification debt increased. UNKNOWN is not FALSE.', 'medium')
ON CONFLICT DO NOTHING;

INSERT INTO verification_requests (document_id, application_id, route, issuer_id, status, ps_status)
VALUES (
    'cccc0005-0005-0005-0005-000000000005',
    'bbbb0001-0001-0001-0001-000000000001',
    'reference_lookup',
    'State Government of Karnataka',
    'SOURCE_UNAVAILABLE',
    'SOURCE_UNAVAILABLE'
) ON CONFLICT DO NOTHING;
"""


def main():
    psql = os.path.join(PG_BIN, "psql") if PG_BIN else "psql"
    result = subprocess.run(
        [psql, "-v", "ON_ERROR_STOP=1", DB_NAME],
        input=SEED_SQL, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"STDERR:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("✅ Demo data seeded: Sunrise Institute, 7 users (password: demo123), "
          "seeded findings + diagnosis")
    print("   Defects: D04 (date inconsistency), D13 (source unavailable)")
    print("   Diagnosis: seeded static — label shown in UI")


if __name__ == "__main__":
    main()
