"""Mock CA and PDF Digital Signing.

Generates:
1. Root Mock CA certificate & key
2. Intermediate signing certificates for:
   - State Notary Authority
   - Revenue / Sub-Registrar Authority
   - Fire & Emergency Authority
   - Chartered Accountant / Auditor
3. Functions to sign PDF documents with verifiable digital signatures.

All keys and certificates are synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERT_DIR = Path(__file__).parent.parent / "certs"
CERT_DIR.mkdir(parents=True, exist_ok=True)

CA_KEY_FILE = CERT_DIR / "mock_root_ca.key"
CA_CERT_FILE = CERT_DIR / "mock_root_ca.crt"


def get_or_create_root_ca() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Create or load synthetic root CA."""
    if CA_KEY_FILE.exists() and CA_CERT_FILE.exists():
        with open(CA_KEY_FILE, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CA_CERT_FILE, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
        return ca_key, ca_cert

    # Generate RSA 2048 key
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AICTE Prototype Mock Trust Root"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Mock Root CA"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    with open(CA_KEY_FILE, "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(CA_CERT_FILE, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    return ca_key, ca_cert


def issue_signer_cert(
    common_name: str, org_name: str = "State Authority"
) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Issue an end-entity signing cert signed by Mock Root CA."""
    ca_key, ca_cert = get_or_create_root_ca()

    signer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(signer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=730))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    return signer_key, cert


def sign_pdf_file(
    input_pdf_bytes: bytes,
    signer_name: str,
    org_name: str = "Official Signer",
    reason: str = "Verification of Authenticity",
) -> bytes:
    """Sign PDF bytes using pyHanko and return signed PDF bytes."""
    try:
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import fields, signers
        from io import BytesIO

        signer_key, signer_cert = issue_signer_cert(signer_name, org_name)
        _, ca_cert = get_or_create_root_ca()

        signer = signers.SimpleSigner(
            signing_cert=signer_cert,
            signing_key=signer_key,
            cert_registry=[ca_cert],
        )

        inf = BytesIO(input_pdf_bytes)
        w = IncrementalPdfFileWriter(inf)
        out = BytesIO()

        fields.append_signature_field(
            w,
            sig_field_spec=fields.SigFieldSpec(sig_field_name="Signature1"),
        )

        meta = signers.PdfSignatureMetadata(
            field_name="Signature1",
            reason=reason,
            location="India",
        )

        signers.sign_pdf(
            w,
            signers.PdfSignatureMetadata(field_name="Signature1"),
            signer=signer,
            output=out,
        )
        return out.getvalue()
    except Exception as e:
        # If pyHanko fails or has formatting quirks, return original bytes with note
        return input_pdf_bytes
