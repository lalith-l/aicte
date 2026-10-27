"""Render-compatible database seeder.

Run from Render Shell:
    python scripts/seed_render.py

Or via the API endpoint POST /api/demo/seed (sysadmin only, demo mode only).

All data is synthetic.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from urllib.parse import urlparse

import psycopg2

from services.api.app.auth.routes import hash_password

PW_HASH = hash_password("demo123")


def get_conn():
    url = os.environ.get("DATABASE_URL", "")
    if url:
        p = urlparse(url)
        return psycopg2.connect(
            dbname=p.path.lstrip("/"),
            user=p.username,
            password=p.password,
            host=p.hostname,
            port=p.port or 5432,
            sslmode="require",
        )
    # Local fallback
    from packages.common.paths import DB_NAME, PG_HOST
    return psycopg2.connect(dbname=DB_NAME, user="app_api", password="app_api_dev", host=PG_HOST)


SEED_SQL = f"""
-- Institutions
INSERT INTO institutions (id, name, code, address, city, state, pin_code)
VALUES
  ('11111111-1111-1111-1111-111111111111','Sunrise Technical Institute','SUNRISE-001','123 Academic Road','Bengaluru','Karnataka','560001'),
  ('22222222-2222-2222-2222-222222222222','Horizon Engineering College','HORIZON-001','456 University Ave','Chennai','Tamil Nadu','600001'),
  ('33333333-3333-3333-3333-333333333333','Pinnacle College of Science','PINNACLE-001','789 Knowledge Park','Hyderabad','Telangana','500001'),
  ('44444444-4444-4444-4444-444444444444','Greenfield Institute of Technology','GIT-001','101 Metro Way','Pune','Maharashtra','411001'),
  ('55555555-5555-5555-5555-555555555555','Westland Engineering College','WEC-001','202 Ring Road','Ahmedabad','Gujarat','380001'),
  ('66666666-6666-6666-6666-666666666666','Rajendra Institute of Management','RIM-001','303 Palace Road','Jaipur','Rajasthan','302001'),
  ('77777777-7777-7777-7777-777777777777','Northstar Academy of Sciences','NAS-001','404 Salt Lake','Kolkata','West Bengal','700001'),
  ('88888888-8888-8888-8888-888888888888','Eastern Polytechnic Institute','EPI-001','505 Infocity','Bhubaneswar','Odisha','751001')
ON CONFLICT (code) DO NOTHING;

-- Users (password: demo123)
INSERT INTO users (id, username, email, pw_hash, role, institution_id) VALUES
  ('aaaa0001-0001-0001-0001-000000000001','sunrise_admin','admin@sunrise.edu','{PW_HASH}','institution_user','11111111-1111-1111-1111-111111111111'),
  ('aaaa0002-0002-0002-0002-000000000002','officer_raj','raj@aicte.gov','{PW_HASH}','scrutiny_officer',NULL),
  ('aaaa0003-0003-0003-0003-000000000003','supervisor_priya','priya@aicte.gov','{PW_HASH}','supervisor',NULL),
  ('aaaa0004-0004-0004-0004-000000000004','auditor_amit','amit@aicte.gov','{PW_HASH}','auditor',NULL),
  ('aaaa0005-0005-0005-0005-000000000005','rules_meera','meera@aicte.gov','{PW_HASH}','rules_admin',NULL),
  ('aaaa0006-0006-0006-0006-000000000006','sysadmin_dev','dev@aicte.gov','{PW_HASH}','sysadmin',NULL),
  ('aaaa0007-0007-0007-0007-000000000007','horizon_admin','admin@horizon.edu','{PW_HASH}','institution_user','22222222-2222-2222-2222-222222222222')
ON CONFLICT (username) DO NOTHING;

-- Applications
INSERT INTO applications (id, institution_id, declared_category, academic_year, stage) VALUES
  ('bbbb0001-0001-0001-0001-000000000001','11111111-1111-1111-1111-111111111111','EOA Renewal','2025-26','UNDER_REVIEW'),
  ('bbbb0002-0002-0002-0002-000000000002','22222222-2222-2222-2222-222222222222','New Approval','2025-26','SUBMITTED'),
  ('bbbb0003-0003-0003-0003-000000000003','33333333-3333-3333-3333-333333333333','EOA Renewal','2025-26','DECISION_PENDING'),
  ('bbbb0004-0004-0004-0004-000000000004','44444444-4444-4444-4444-444444444444','Intake Enhancement','2025-26','APPROVED'),
  ('bbbb0005-0005-0005-0005-000000000005','55555555-5555-5555-5555-555555555555','EOA Renewal','2025-26','REJECTED'),
  ('bbbb0006-0006-0006-0006-000000000006','66666666-6666-6666-6666-666666666666','New Approval','2025-26','EXTRACTING'),
  ('bbbb0007-0007-0007-0007-000000000007','77777777-7777-7777-7777-777777777777','EOA Renewal','2025-26','UNDER_REVIEW'),
  ('bbbb0008-0008-0008-0008-000000000008','88888888-8888-8888-8888-888888888888','Intake Enhancement','2025-26','INGESTING')
ON CONFLICT DO NOTHING;

-- Documents
INSERT INTO documents (id, application_id, type_declared, file_ref, sha256, page_count) VALUES
  ('cccc0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001','Trust Deed','sunrise/trust_deed.pdf','a1b2c3d4e5f6',3),
  ('cccc0002-0002-0002-0002-000000000002','bbbb0001-0001-0001-0001-000000000001','Affidavit','sunrise/affidavit.pdf','b2c3d4e5f6a1',2),
  ('cccc0003-0003-0003-0003-000000000003','bbbb0001-0001-0001-0001-000000000001','Stamp Paper','sunrise/stamp_paper.pdf','c3d4e5f6a1b2',1),
  ('cccc0004-0004-0004-0004-000000000004','bbbb0001-0001-0001-0001-000000000001','Faculty List','sunrise/faculty_list.pdf','d4e5f6a1b2c3',5),
  ('cccc0005-0005-0005-0005-000000000005','bbbb0001-0001-0001-0001-000000000001','NOC Certificate','sunrise/noc_certificate.pdf','e5f6a1b2c3d4',1),
  ('cccc0031-0031-0031-0031-000000000031','bbbb0003-0003-0003-0003-000000000003','Trust Deed','pinnacle/trust_deed.pdf','p1p2p3p4p5p6',4),
  ('cccc0032-0032-0032-0032-000000000032','bbbb0003-0003-0003-0003-000000000003','Land Certificate','pinnacle/land_deed.pdf','l1l2l3l4l5l6',6),
  ('cccc0033-0033-0033-0033-000000000033','bbbb0003-0003-0003-0003-000000000003','Fire Safety','pinnacle/fire_safety.pdf','f1f2f3f4f5f6',2),
  ('cccc0034-0034-0034-0034-000000000034','bbbb0003-0003-0003-0003-000000000003','Faculty Roster','pinnacle/faculty_roster.pdf','r1r2r3r4r5r6',8),
  ('cccc0071-0071-0071-0071-000000000071','bbbb0007-0007-0007-0007-000000000007','Trust Deed','northstar/trust_deed.pdf','n1n2n3n4n5n6',3),
  ('cccc0072-0072-0072-0072-000000000072','bbbb0007-0007-0007-0007-000000000007','Affiliation Order','northstar/affiliation.pdf','a7a7a7a7a7a7',2)
ON CONFLICT DO NOTHING;

-- Findings
INSERT INTO findings (id, application_id, source_code, tier, result, reason, evidence, recheck_recipe) VALUES
  ('dddd0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001','D04-date-inconsistency',1,'FALSE',
   'Affidavit date (2025-01-15) conflicts with stamp paper date (2025-02-01). Stamp purchased after affidavit executed.',
   '{{"documents":["cccc0002-0002-0002-0002-000000000002","cccc0003-0003-0003-0003-000000000003"],"fields":["affidavit_date","stamp_paper_date"]}}',
   'Compare affidavit date with stamp paper date.'),
  ('dddd0002-0002-0002-0002-000000000002','bbbb0001-0001-0001-0001-000000000001','D13-source-unavailable',2,'UNKNOWN',
   'NOC issuer verification endpoint returned 503. UNKNOWN is not FALSE.',
   '{{"documents":["cccc0005-0005-0005-0005-000000000005"],"status":"SOURCE_UNAVAILABLE"}}',
   'Retry external issuer endpoint with exponential backoff.'),
  ('dddd0031-0031-0031-0031-000000000031','bbbb0003-0003-0003-0003-000000000003','D09-land-area-shortfall',2,'FALSE',
   'Declared land area is 5.0 acres, but verified municipal land registry indicates only 3.8 acres. Deficit of 1.2 acres.',
   '{{"documents":["cccc0032-0032-0032-0032-000000000032"],"fields":["land_area"]}}',
   'Request certified survey map from District Revenue Officer.'),
  ('dddd0032-0032-0032-0032-000000000032','bbbb0003-0003-0003-0003-000000000003','D02-expired-certificate',1,'FALSE',
   'Fire & Safety certificate expired on 2024-12-31 prior to application submission.',
   '{{"documents":["cccc0033-0033-0033-0033-000000000033"],"fields":["expiry_date"]}}',
   'Upload valid renewed Fire & Safety NOC from Fire Department.')
ON CONFLICT DO NOTHING;

-- Document statuses
INSERT INTO document_status (id, document_id, status, source) VALUES
  ('ffff0001-0001-0001-0001-000000000001','cccc0001-0001-0001-0001-000000000001','VERIFIED','signature_check'),
  ('ffff0002-0002-0002-0002-000000000002','cccc0002-0002-0002-0002-000000000002','VERIFIED','signature_check'),
  ('ffff0003-0003-0003-0003-000000000003','cccc0003-0003-0003-0003-000000000003','VERIFIED','signature_check'),
  ('ffff0004-0004-0004-0004-000000000004','cccc0004-0004-0004-0004-000000000004','MANUAL_REVIEW_REQUIRED','extraction_disagreement'),
  ('ffff0005-0005-0005-0005-000000000005','cccc0005-0005-0005-0005-000000000005','SOURCE_UNAVAILABLE','issuer_503'),
  ('ffff0031-0031-0031-0031-000000000031','cccc0031-0031-0031-0031-000000000031','VERIFIED','signature_check'),
  ('ffff0032-0032-0032-0032-000000000032','cccc0032-0032-0032-0032-000000000032','MISMATCH_DETECTED','land_record_crosscheck'),
  ('ffff0033-0033-0033-0033-000000000033','cccc0033-0033-0033-0033-000000000033','EXPIRED','date_check'),
  ('ffff0034-0034-0034-0034-000000000034','cccc0034-0034-0034-0034-000000000034','MANUAL_REVIEW_REQUIRED','faculty_ratio'),
  ('ffff0071-0071-0071-0071-000000000071','cccc0071-0071-0071-0071-000000000071','VERIFIED','signature_check'),
  ('ffff0072-0072-0072-0072-000000000072','cccc0072-0072-0072-0072-000000000072','VERIFIED','university_portal')
ON CONFLICT DO NOTHING;

-- Risk scores
INSERT INTO risk_scores (id, application_id, score, model_version) VALUES
  ('10000001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001', 0.73, 'seed-static'),
  ('10000002-0002-0002-0002-000000000002','bbbb0002-0002-0002-0002-000000000002', 0.21, 'seed-static'),
  ('10000003-0003-0003-0003-000000000003','bbbb0003-0003-0003-0003-000000000003', 0.88, 'seed-static'),
  ('10000004-0004-0004-0004-000000000004','bbbb0004-0004-0004-0004-000000000004', 0.12, 'seed-static'),
  ('10000005-0005-0005-0005-000000000005','bbbb0005-0005-0005-0005-000000000005', 0.95, 'seed-static'),
  ('10000006-0006-0006-0006-000000000006','bbbb0006-0006-0006-0006-000000000006', 0.45, 'seed-static'),
  ('10000007-0007-0007-0007-000000000007','bbbb0007-0007-0007-0007-000000000007', 0.62, 'seed-static')
ON CONFLICT DO NOTHING;

-- Review items
INSERT INTO review_items (id, application_id, level, reason, assignee, state) VALUES
  ('eeee0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001',2,'Sunrise D04+D13 review','aaaa0002-0002-0002-0002-000000000002','assigned'),
  ('eeee0002-0002-0002-0002-000000000002','bbbb0003-0003-0003-0003-000000000003',3,'Pinnacle D09 Land Deficit & D02 Expired Cert',NULL,'pending'),
  ('eeee0003-0003-0003-0003-000000000003','bbbb0007-0007-0007-0007-000000000007',2,'Northstar Tier 2 Verification','aaaa0003-0003-0003-0003-000000000003','assigned'),
  ('eeee0004-0004-0004-0004-000000000004','bbbb0006-0006-0006-0006-000000000006',1,'Rajendra Incomplete Extraction',NULL,'pending'),
  ('eeee0005-0005-0005-0005-000000000005','bbbb0002-0002-0002-0002-000000000002',0,'Horizon Automated Level 0 Clearance',NULL,'pending')
ON CONFLICT DO NOTHING;

-- Alerts
INSERT INTO alerts (id, type, application_id, message, severity) VALUES
  ('al0001','FINDING_RAISED','bbbb0001-0001-0001-0001-000000000001','D04 date inconsistency on Sunrise affidavit vs stamp paper','high'),
  ('al0002','SOURCE_OUTAGE','bbbb0001-0001-0001-0001-000000000001','NOC issuer 503 — verification debt increased. UNKNOWN is not FALSE.','medium'),
  ('al0003','FINDING_RAISED','bbbb0003-0003-0003-0003-000000000003','D09 land deficit: 3.8 acres verified vs 5.0 acres required','high'),
  ('al0004','EXTRACTION_UNCERTAIN','bbbb0006-0006-0006-0006-000000000006','Rajendra Institute extraction confidence below 0.65; routed to queue','low')
ON CONFLICT DO NOTHING;
"""


def seed():
    conn = get_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(SEED_SQL)
        conn.commit()
        print("✅ Render DB seeded successfully!")
        print("   Institutions: Sunrise Technical Institute, Horizon Engineering College")
        print("   Users (all password: demo123):")
        print("     sunrise_admin / officer_raj / supervisor_priya")
        print("     auditor_amit / rules_meera / sysadmin_dev / horizon_admin")
        print("   Application: bbbb0001 — UNDER_REVIEW with D04+D13 findings")
    except Exception as e:
        conn.rollback()
        print(f"❌ Seed failed: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
