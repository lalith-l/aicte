"""Mock Issuers and Consent Server.

Simulates official verification authorities with:
1. Land Registry / Revenue Department
2. State Higher Education Dept (NOC)
3. University Affiliation Body
4. Fire & Emergency Services
5. Municipal Building Authority
6. Bank / Financial Institution (FDR)

Features:
- JWS (ES256) signed responses
- OAuth2 + PKCE Consent Flow for consented fetch
- Chaos mode (configurable 503 / outage / latency)
- All data is synthetic
- PLACEHOLDER for all handbook clause references
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from fastapi import FastAPI, HTTPException, Query, Header, Depends, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="AICTE Prototype — Mock Issuers & Consent Server",
    description="Simulated government and statutory issuers with JWS ES256 signing and PKCE consent",
)

# ---------------------------------------------------------------------------
# Key Management (ES256 for JWS)
# ---------------------------------------------------------------------------
KEYS_DIR = Path(__file__).parent / "keys"
KEYS_DIR.mkdir(parents=True, exist_ok=True)
KEY_FILE = KEYS_DIR / "issuer_es256.pem"

if KEY_FILE.exists():
    with open(KEY_FILE, "rb") as f:
        _private_key = serialization.load_pem_private_key(f.read(), password=None)
else:
    _private_key = ec.generate_private_key(ec.SECP256R1())
    with open(KEY_FILE, "wb") as f:
        f.write(
            _private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

_public_key = _private_key.public_key()
_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

# ---------------------------------------------------------------------------
# Chaos state
# ---------------------------------------------------------------------------
_chaos_enabled = False
_chaos_outage_rate = 0.7  # 70% rate of 503 when enabled
_chaos_latency_ms = 0     # injected latency

def _check_chaos():
    if _chaos_enabled:
        if _chaos_latency_ms > 0:
            time.sleep(_chaos_latency_ms / 1000.0)
        if random.random() < _chaos_outage_rate:
            raise HTTPException(
                status_code=503,
                detail="SOURCE_UNAVAILABLE: Issuer service endpoint temporarily unreachable (simulated chaos outage)",
            )

# ---------------------------------------------------------------------------
# JWS ES256 Signer
# ---------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def sign_jws_payload(payload: dict, issuer_name: str) -> str:
    """Signs payload into a compact JWS (ES256)."""
    header = {
        "alg": "ES256",
        "typ": "JWT",
        "iss": issuer_name,
        "kid": f"{issuer_name}-key-1",
    }
    header_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    # Sign using ECDSA with SHA-256
    sig_der = _private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    # Convert DER to raw r||s (64 bytes)
    r, s = ec.util.decode_dss_signature(sig_der)
    raw_sig = r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big")
    sig_b64 = _b64url_encode(raw_sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

# ---------------------------------------------------------------------------
# Verification Models
# ---------------------------------------------------------------------------
class VerificationRequest(BaseModel):
    document_id: str
    institution_code: str
    reference_number: str
    claimed_fields: dict
    nonce: Optional[str] = None

class VerificationResponse(BaseModel):
    issuer: str
    status: str  # VERIFIED, UNVERIFIED, SOURCE_UNAVAILABLE, NOT_IN_JURISDICTION
    verified_at: str
    reference_number: str
    record: Optional[dict] = None
    discrepancies: list[str] = []
    jws_token: str
    is_synthetic: bool = True
    clause_ref_placeholder: str = "PLACEHOLDER"

# ---------------------------------------------------------------------------
# Issuer Endpoints
# ---------------------------------------------------------------------------

@app.get("/issuers/public_key")
def get_public_key():
    """Return issuer public key for signature verification."""
    return {"format": "PEM", "algorithm": "ES256", "public_key": _public_pem}

@app.post("/issuers/chaos/enable")
def enable_chaos(outage_rate: float = 0.7, latency_ms: int = 0):
    global _chaos_enabled, _chaos_outage_rate, _chaos_latency_ms
    _chaos_enabled = True
    _chaos_outage_rate = outage_rate
    _chaos_latency_ms = latency_ms
    return {"status": "ok", "chaos_enabled": True, "outage_rate": _chaos_outage_rate}

@app.post("/issuers/chaos/disable")
def disable_chaos():
    global _chaos_enabled
    _chaos_enabled = False
    return {"status": "ok", "chaos_enabled": False}

@app.get("/issuers/chaos/status")
def chaos_status():
    return {
        "chaos_enabled": _chaos_enabled,
        "outage_rate": _chaos_outage_rate,
        "latency_ms": _chaos_latency_ms,
        "synthetic": True,
    }

# 1. Land & Revenue Authority
@app.post("/issuers/land/verify", response_model=VerificationResponse)
def verify_land(req: VerificationRequest):
    _check_chaos()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "deed_number": req.reference_number,
        "institution_code": req.institution_code,
        "survey_numbers": ["102/1A", "102/1B", "103/2"],
        "area_acres": 5.25,
        "land_category": "Institutional",
        "encumbrance_status": "CLEAR",
        "registered_owner": f"{req.institution_code} Education Trust",
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
    jws = sign_jws_payload(record, "RevenueDept-LandRecords")
    return VerificationResponse(
        issuer="RevenueDept-LandRecords",
        status="VERIFIED",
        verified_at=now,
        reference_number=req.reference_number,
        record=record,
        discrepancies=[],
        jws_token=jws,
    )

@app.post("/issuers/other_state/verify", response_model=VerificationResponse)
def verify_other_state(req: VerificationRequest):
    now = datetime.now(timezone.utc).isoformat()
    jws = sign_jws_payload({"declined": True, "synthetic": True}, "OtherStateAuthority")
    return VerificationResponse(
        issuer="OtherStateAuthority",
        status="NOT_IN_JURISDICTION",
        verified_at=now,
        reference_number=req.reference_number,
        record=None,
        discrepancies=["Record belongs to another state authority"],
        jws_token=jws,
    )


# 2. State Higher Education Department (NOC)
@app.post("/issuers/state_noc/verify", response_model=VerificationResponse)
@app.post("/issuers/noc/verify", response_model=VerificationResponse)
def verify_state_noc(req: VerificationRequest):
    _check_chaos()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "noc_number": req.reference_number,
        "institution_code": req.institution_code,
        "academic_year": "2025-26",
        "valid_till": (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d"),
        "programmes_permitted": ["Engineering & Technology", "Management"],
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
    jws = sign_jws_payload(record, "StateHigherEducationDept")
    return VerificationResponse(
        issuer="StateHigherEducationDept",
        status="VERIFIED",
        verified_at=now,
        reference_number=req.reference_number,
        record=record,
        discrepancies=[],
        jws_token=jws,
    )

# 3. Fire & Emergency Services NOC
@app.post("/issuers/fire_safety/verify", response_model=VerificationResponse)
def verify_fire_safety(req: VerificationRequest):
    _check_chaos()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "certificate_number": req.reference_number,
        "institution_code": req.institution_code,
        "inspection_date": "2025-01-15",
        "expiry_date": "2026-01-14",
        "compliance_status": "COMPLIANT",
        "floors_inspected": "Ground + 3 Floors",
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
    jws = sign_jws_payload(record, "FireSafetyServices")
    return VerificationResponse(
        issuer="FireSafetyServices",
        status="VERIFIED",
        verified_at=now,
        reference_number=req.reference_number,
        record=record,
        discrepancies=[],
        jws_token=jws,
    )

# 4. Building Approval Authority
@app.post("/issuers/building_plan/verify", response_model=VerificationResponse)
def verify_building_plan(req: VerificationRequest):
    _check_chaos()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "plan_approval_number": req.reference_number,
        "institution_code": req.institution_code,
        "built_up_area_sqm": 8500.0,
        "fsi_utilization": 1.2,
        "approval_date": "2023-08-20",
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
    jws = sign_jws_payload(record, "MunicipalBuildingAuthority")
    return VerificationResponse(
        issuer="MunicipalBuildingAuthority",
        status="VERIFIED",
        verified_at=now,
        reference_number=req.reference_number,
        record=record,
        discrepancies=[],
        jws_token=jws,
    )

# 5. Bank / FDR Verification
@app.post("/issuers/bank/verify", response_model=VerificationResponse)
def verify_bank_fdr(req: VerificationRequest):
    _check_chaos()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "fdr_number": req.reference_number,
        "institution_code": req.institution_code,
        "fdr_amount": 10000000,  # 1 Crore
        "maturity_date": "2028-12-31",
        "lien_marked_to": "AICTE",
        "status": "ACTIVE",
        "synthetic": True,
        "norm_clause": "PLACEHOLDER",
    }
    jws = sign_jws_payload(record, "ScheduledCommercialBank")
    return VerificationResponse(
        issuer="ScheduledCommercialBank",
        status="VERIFIED",
        verified_at=now,
        reference_number=req.reference_number,
        record=record,
        discrepancies=[],
        jws_token=jws,
    )

# ---------------------------------------------------------------------------
# OAuth2 + PKCE Consent Flow
# ---------------------------------------------------------------------------
# In-memory store for authorization codes
_auth_codes: dict[str, dict] = {}
_access_tokens: dict[str, dict] = {}

@app.post("/issuers/oauth/authorize")
def oauth_authorize(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
    scope: str = Form(...),
    institution_code: str = Form(...),
):
    """Simulated consent approval by institution authorized officer."""
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Only S256 code_challenge_method supported")
    
    auth_code = f"auth_code_{uuid.uuid4().hex[:16]}"
    _auth_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "scope": scope,
        "institution_code": institution_code,
        "created_at": time.time(),
    }
    return {
        "code": auth_code,
        "redirect_to": f"{redirect_uri}?code={auth_code}",
        "message": "Consent granted by institution signatory (simulated)",
    }

@app.post("/issuers/oauth/token")
def oauth_token(
    client_id: str = Form(...),
    code: str = Form(...),
    code_verifier: str = Form(...),
    redirect_uri: str = Form(...),
):
    """Exchange authorization code with PKCE code_verifier for access token."""
    code_data = _auth_codes.get(code)
    if not code_data:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")
    
    # Verify PKCE code_verifier: BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) == code_challenge
    computed_challenge = _b64url_encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
    if computed_challenge != code_data["code_challenge"]:
        raise HTTPException(status_code=400, detail="PKCE verification failed: challenge mismatch")

    # Clean up code
    del _auth_codes[code]

    token = f"inst_token_{uuid.uuid4().hex}"
    _access_tokens[token] = {
        "institution_code": code_data["institution_code"],
        "scope": code_data["scope"],
        "expires_at": time.time() + 3600,
    }

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": code_data["scope"],
    }

@app.get("/issuers/consented/fetch")
def consented_fetch(
    data_type: str = Query(...),
    authorization: str = Header(None),
):
    """Fetch external records using consented token."""
    _check_chaos()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    
    token = authorization.split(" ")[1]
    token_data = _access_tokens.get(token)
    if not token_data or token_data["expires_at"] < time.time():
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    inst_code = token_data["institution_code"]
    return {
        "institution_code": inst_code,
        "data_type": data_type,
        "status": "VERIFIED_VIA_CONSENT",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "authority": "ConsentedStatutoryGateway",
            "institution_code": inst_code,
            "verified": True,
            "placeholder_norm": "PLACEHOLDER",
        },
        "synthetic": True,
    }
