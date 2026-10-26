"""Mock CA + optional pyHanko signing for synthetic PDFs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from packages.common.paths import CERT_DIR


def ensure_mock_ca() -> tuple[Path, Path]:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key_path = CERT_DIR / "mock_ca.key"
    cert_path = CERT_DIR / "mock_ca.pem"
    if key_path.exists() and cert_path.exists():
        return key_path, cert_path
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AICTE Prototype Mock CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Trust Root"),
        ]
    )
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key_path, cert_path


def sign_pdf(pdf_path: Path) -> bool:
    """Best-effort pyHanko sign. Returns False if signing libraries are unavailable."""
    ensure_mock_ca()
    try:
        from pyhanko.sign import signers
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        signer = signers.SimpleSigner.load(
            str(CERT_DIR / "mock_ca.key"),
            str(CERT_DIR / "mock_ca.pem"),
        )
        out = pdf_path.with_suffix(".signed.pdf")
        with pdf_path.open("rb") as inf, out.open("wb") as outf:
            w = IncrementalPdfFileWriter(inf)
            signers.sign_pdf(w, signers.PdfSignatureMetadata(field_name="Sig1"), signer=signer, output=outf)
        out.replace(pdf_path)
        return True
    except Exception:
        return False
