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
  ('22222222-2222-2222-2222-222222222222','Horizon Engineering College','HORIZON-001','456 University Ave','Chennai','Tamil Nadu','600001')
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

-- Application
INSERT INTO applications (id, institution_id, declared_category, academic_year, stage)
VALUES ('bbbb0001-0001-0001-0001-000000000001','11111111-1111-1111-1111-111111111111','eoa_renewal','2025-26','UNDER_REVIEW')
ON CONFLICT DO NOTHING;

-- Documents
INSERT INTO documents (id, application_id, type_declared, file_ref, sha256, page_count) VALUES
  ('cccc0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001','trust_deed','sunrise/trust_deed.pdf','a1b2c3d4e5f6',3),
  ('cccc0002-0002-0002-0002-000000000002','bbbb0001-0001-0001-0001-000000000001','affidavit','sunrise/affidavit.pdf','b2c3d4e5f6a1',2),
  ('cccc0003-0003-0003-0003-000000000003','bbbb0001-0001-0001-0001-000000000001','stamp_paper','sunrise/stamp_paper.pdf','c3d4e5f6a1b2',1),
  ('cccc0004-0004-0004-0004-000000000004','bbbb0001-0001-0001-0001-000000000001','faculty_list','sunrise/faculty_list.pdf','d4e5f6a1b2c3',5),
  ('cccc0005-0005-0005-0005-000000000005','bbbb0001-0001-0001-0001-000000000001','noc','sunrise/noc_certificate.pdf','e5f6a1b2c3d4',1)
ON CONFLICT DO NOTHING;

-- Findings
INSERT INTO findings (id, application_id, source_code, tier, result, reason, evidence, recheck_recipe) VALUES
  ('dddd0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001','D04-date-inconsistency',1,'FALSE',
   'Affidavit date (2025-01-15) conflicts with stamp paper date (2025-02-01). Stamp purchased after affidavit executed.',
   '{{"documents":["cccc0002-0002-0002-0002-000000000002","cccc0003-0003-0003-0003-000000000003"],"fields":["affidavit_date","stamp_paper_date"]}}',
   'Compare affidavit date with stamp paper date.')
ON CONFLICT DO NOTHING;

INSERT INTO findings (id, application_id, source_code, tier, result, reason, evidence) VALUES
  ('dddd0002-0002-0002-0002-000000000002','bbbb0001-0001-0001-0001-000000000001','D13-source-unavailable',2,'UNKNOWN',
   'NOC issuer verification endpoint returned 503. UNKNOWN is not FALSE.',
   '{{"documents":["cccc0005-0005-0005-0005-000000000005"],"status":"SOURCE_UNAVAILABLE"}}')
ON CONFLICT DO NOTHING;

-- Document statuses
INSERT INTO document_status (document_id, status, source) VALUES
  ('cccc0001-0001-0001-0001-000000000001','VERIFIED','signature_check'),
  ('cccc0002-0002-0002-0002-000000000002','VERIFIED','signature_check'),
  ('cccc0003-0003-0003-0003-000000000003','VERIFIED','signature_check'),
  ('cccc0004-0004-0004-0004-000000000004','MANUAL_REVIEW_REQUIRED','extraction_disagreement'),
  ('cccc0005-0005-0005-0005-000000000005','SOURCE_UNAVAILABLE','issuer_503')
ON CONFLICT DO NOTHING;

-- Risk score
INSERT INTO risk_scores (application_id, score, model_version)
VALUES ('bbbb0001-0001-0001-0001-000000000001', 0.73, 'seed-static')
ON CONFLICT DO NOTHING;

-- Review item
INSERT INTO review_items (id, application_id, level, reason, assignee, state)
VALUES ('eeee0001-0001-0001-0001-000000000001','bbbb0001-0001-0001-0001-000000000001',2,'Sunrise D04+D13','aaaa0002-0002-0002-0002-000000000002','assigned')
ON CONFLICT DO NOTHING;

-- Alerts
INSERT INTO alerts (type, application_id, message, severity) VALUES
  ('FINDING_RAISED','bbbb0001-0001-0001-0001-000000000001','D04 date inconsistency on Sunrise affidavit vs stamp paper','high'),
  ('SOURCE_OUTAGE','bbbb0001-0001-0001-0001-000000000001','NOC issuer 503 — verification debt increased. UNKNOWN is not FALSE.','medium')
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
