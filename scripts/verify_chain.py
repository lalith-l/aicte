"""Verify the audit chain and every published head hash.

Usage: python scripts/verify_chain.py [--publish]
Exit code 0 = chain intact and consistent with every published head, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2  # noqa: E402

from packages.audit.chain import full_report, publish_head  # noqa: E402
from packages.common.paths import DB_NAME, PG_HOST  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="publish today's head hash first")
    args = ap.parse_args()
    conn = psycopg2.connect(
        dbname=DB_NAME, host=PG_HOST, user="app_readonly", password="app_readonly_dev"
    )
    try:
        if args.publish:
            print("published:", publish_head(conn))
        rep = full_report(conn)
        print(json.dumps(rep, indent=2, default=str))
        return 0 if rep["all_ok"] else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
