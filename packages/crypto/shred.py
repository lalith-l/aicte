"""Crypto-shred: DELETE the file_keys row so ciphertext on disk is unrecoverable.

Authority: only deterministic retention jobs / sysadmin call this.
All data is synthetic.
"""
from __future__ import annotations

from pathlib import Path


def shred_document(conn, document_id: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT file_ref FROM documents WHERE id = %s", (document_id,))
    row = cur.fetchone()
    cur.execute("DELETE FROM file_keys WHERE document_id = %s", (document_id,))
    deleted = cur.rowcount
    cur.close()
    if row and row[0]:
        path = Path(row[0])
        if path.exists() and path.suffix == ".enc":
            path.unlink(missing_ok=True)
    return deleted > 0


def file_is_unrecoverable(conn, document_id: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM file_keys WHERE document_id = %s", (document_id,))
    has_key = cur.fetchone() is not None
    cur.close()
    return not has_key
