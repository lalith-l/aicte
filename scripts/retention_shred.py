"""Retention job: crypto-shred documents past the configured retention window.

All data is synthetic. Never run against real records.
"""
from __future__ import annotations

import os
import sys

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.common.paths import DB_NAME, PG_HOST  # noqa: E402
from packages.crypto.shred import shred_document  # noqa: E402

RETENTION_DAYS = int(os.environ.get("AICTE_RETENTION_DAYS", "365"))


def main() -> None:
    conn = psycopg2.connect(dbname=DB_NAME, user="app_det", password="app_det_dev", host=PG_HOST)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM documents WHERE created_at < NOW() - (%s || ' days')::interval",
        (str(RETENTION_DAYS),),
    )
    ids = [str(r[0]) for r in cur.fetchall()]
    n = 0
    for did in ids:
        if shred_document(conn, did):
            n += 1
    conn.commit()
    conn.close()
    print(f"shredded {n} keys (synthetic)")


if __name__ == "__main__":
    main()
