"""Cryptographic shredding for retention lifecycle.

Performs GDPR/DPDP compliant cryptographic shredding:
1. Irrevocably deletes document encryption key from file_keys (DELETE allowed)
2. Overwrites encrypted file payload on disk with cryptographically secure random bytes
3. Unlinks the file from disk
4. Emits append-only KEY_SHREDDED audit event via audit_append()

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import psycopg2


def crypto_shred_document(
    document_id: str,
    actor_id: str,
    db_conn: psycopg2.extensions.connection,
) -> dict:
    """Shred encryption key and overwrite ciphertext for a document."""
    with db_conn.cursor() as cur:
        # 1. Fetch file storage path
        cur.execute(
            """
            SELECT storage_path FROM file_keys WHERE document_id = %s
            """,
            (document_id,),
        )
        row = cur.fetchone()
        storage_path = row[0] if row else None

        # 2. Delete key row from file_keys (DELETE allowed for retention shredding)
        cur.execute(
            """
            DELETE FROM file_keys WHERE document_id = %s
            """,
            (document_id,),
        )
        keys_deleted = cur.rowcount

        # 3. Securely overwrite file on disk if exists
        disk_shredded = False
        if storage_path and Path(storage_path).exists():
            file_size = os.path.getsize(storage_path)
            with open(storage_path, "wb") as f:
                f.write(os.urandom(file_size))  # Overwrite with secure random
            os.remove(storage_path)
            disk_shredded = True

        # 4. Append audit log entry
        cur.execute(
            """
            SELECT audit_append(%s, %s, %s, %s, %s)
            """,
            (
                "KEY_SHREDDED",
                "documents",
                document_id,
                actor_id,
                f'{{"keys_deleted": {keys_deleted}, "disk_shredded": {str(disk_shredded).lower()}}}',
            ),
        )

    db_conn.commit()
    return {
        "document_id": document_id,
        "key_shredded": keys_deleted > 0,
        "disk_shredded": disk_shredded,
        "status": "SHREDDED",
        "synthetic": True,
    }
