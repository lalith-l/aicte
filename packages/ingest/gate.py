"""Ingestion gate for document processing.

Enforces:
1. Magic bytes verification (PDF, PNG, JPEG, TIFF)
2. Decompression ratio check (zip/PDF bomb defense)
3. Encrypted/password-protected PDF detection -> UNREADABLE
4. Per-file AES-256-GCM encryption with keys stored in file_keys
5. File storage under UUIDs
6. SHA-256 content hash
7. Append-only audit logging via audit_append()

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sys
import uuid
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import psycopg2

from packages.common.paths import STORAGE_DIR

STORAGE_ROOT = STORAGE_DIR
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_DECOMPRESSION_RATIO = 100.0  # defense against compression bombs


class IngestionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def verify_magic_bytes(data: bytes) -> str:
    """Verify magic bytes and return detected MIME/format type."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "image/tiff"
    else:
        raise IngestionError("INVALID_FORMAT", "File does not match supported magic bytes (PDF, PNG, JPEG, TIFF)")


def check_pdf_security_and_decompression(data: bytes) -> tuple[int, bool]:
    """Check if PDF is encrypted or has dangerous decompression ratio.
    
    Returns (page_count, is_encrypted).
    """
    if not data.startswith(b"%PDF-"):
        return 1, False

    try:
        import pikepdf
        from io import BytesIO

        try:
            with pikepdf.open(BytesIO(data)) as pdf:
                page_count = len(pdf.pages)
                # Check stream sizes for bomb detection
                total_uncompressed = 0
                compressed_seen = 0
                for obj in pdf.objects:
                    if isinstance(obj, pikepdf.Stream):
                        try:
                            compressed_seen += len(obj.read_raw_bytes())
                            total_uncompressed += len(obj.read_bytes())
                        except Exception:
                            pass
                if compressed_seen > 0 and (total_uncompressed / compressed_seen) > MAX_DECOMPRESSION_RATIO:
                    raise IngestionError("DECOMPRESSION_BOMB", "PDF exceeds maximum safe decompression ratio")
                return page_count, False
        except pikepdf.PasswordError:
            # Encrypted PDF -> Safe flag as UNREADABLE
            return 0, True
    except IngestionError:
        raise
    except Exception as e:
        # Fallback inspection if pikepdf raises syntax error
        if b"/Encrypt" in data:
            return 0, True
        return 1, False


def encrypt_and_store_file(
    data: bytes,
    document_id: str,
    conn: Optional[psycopg2.extensions.connection] = None,
) -> tuple[str, str, bytes]:
    """Encrypt payload with AES-256-GCM, store on disk, record key in file_keys.
    
    Returns (storage_path, sha256_hash, key).
    """
    key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    stored_payload = nonce + ciphertext

    file_uuid = uuid.uuid4().hex
    target_path = STORAGE_ROOT / f"{file_uuid}.enc"
    with open(target_path, "wb") as f:
        f.write(stored_payload)

    sha256_hash = hashlib.sha256(data).hexdigest()

    if conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO file_keys (document_id, encrypted_key, nonce)
                VALUES (%s, %s, %s)
                """,
                (document_id, key, nonce),
            )

    return str(target_path), sha256_hash, key


def decrypt_stored_file(storage_path: str, key_hex: str) -> bytes:
    """Decrypt AES-256-GCM file from disk."""
    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)
    with open(storage_path, "rb") as f:
        content = f.read()
    nonce = content[:12]
    ciphertext = content[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def ingest_document(
    data: bytes,
    application_id: str,
    declared_type: str,
    actor_id: Optional[str] = None,
    conn: Optional[psycopg2.extensions.connection] = None,
) -> dict:
    """Full ingestion pipeline for a document."""
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise IngestionError("FILE_TOO_LARGE", f"File size exceeds 50MB limit ({len(data)} bytes)")

    mime_type = verify_magic_bytes(data)
    page_count, is_encrypted = check_pdf_security_and_decompression(data)

    doc_id = str(uuid.uuid4())
    storage_path, sha256_hash, _ = encrypt_and_store_file(data, doc_id, conn)

    status = "UNREADABLE" if is_encrypted else "INGESTED"

    if conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (id, application_id, type_declared, file_ref, sha256, page_count, mime_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (doc_id, application_id, declared_type, storage_path, sha256_hash, page_count, mime_type),
            )
            db_status = "MANUAL_REVIEW_REQUIRED" if is_encrypted else "VERIFICATION_PENDING"
            cur.execute(
                """
                INSERT INTO document_status (document_id, status, source)
                VALUES (%s, %s, %s)
                """,
                (
                    doc_id,
                    db_status,
                    "encrypted_pdf_unreadable" if is_encrypted else "ingestion_gate",
                ),
            )
            import json as _json

            cur.execute(
                "SELECT audit_append(%s, %s, %s::jsonb)",
                (
                    actor_id or "ingest_gate",
                    "document_ingested",
                    _json.dumps(
                        {
                            "document_id": doc_id,
                            "sha256": sha256_hash,
                            "status": status,
                            "pages": page_count,
                            "synthetic_data": True,
                        }
                    ),
                ),
            )

    return {
        "document_id": doc_id,
        "application_id": application_id,
        "mime_type": mime_type,
        "page_count": page_count,
        "sha256": sha256_hash,
        "storage_path": storage_path,
        "status": status,
        "is_encrypted": is_encrypted,
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
