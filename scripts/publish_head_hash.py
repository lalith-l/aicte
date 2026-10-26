"""Publish today's audit-chain head hash to data/mail/."""
from __future__ import annotations

import os
import sys

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.audit.chain import publish_head  # noqa: E402
from packages.common.paths import DB_NAME, PG_HOST  # noqa: E402


def main() -> None:
    conn = psycopg2.connect(dbname=DB_NAME, user="app_api", password="app_api_dev", host=PG_HOST)
    path = publish_head(conn)
    conn.close()
    print(path)


if __name__ == "__main__":
    main()
