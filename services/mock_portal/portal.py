"""Mock AICTE portal — simulates the real portal for verification.

Endpoints:
  GET /portal/institution/{code} — returns institution data
  GET /portal/application/{app_id}/intake — returns declared intake
  GET /portal/status — returns portal health

Chaos mode: /portal/chaos/on and /portal/chaos/off toggle 503 responses.
All data is synthetic.
"""
from __future__ import annotations

import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock AICTE Portal", description="Synthetic data only")

# State
_chaos_mode = False
_chaos_503_rate = 0.7


class PortalInstitution(BaseModel):
    code: str
    name: str
    status: str
    approved_intake: int
    programmes: list[str]
    synthetic: bool = True


class PortalIntake(BaseModel):
    application_id: str
    approved_intake: int
    actual_intake: int
    mismatch: bool
    synthetic: bool = True


# In-memory store (populated at startup from DB or seed)
_institutions: dict[str, PortalInstitution] = {}


def seed_portal_data(institutions: list[dict]):
    """Seed mock portal with institution data."""
    programmes = ["B.Tech CSE", "B.Tech ECE", "B.Tech ME", "MBA", "MCA", "B.Tech CE", "B.Tech EEE"]
    for inst in institutions:
        code = inst["code"]
        intake = random.randint(60, 300)
        _institutions[code] = PortalInstitution(
            code=code, name=inst["name"], status="APPROVED",
            approved_intake=intake,
            programmes=random.sample(programmes, random.randint(2, 5)),
        )


@app.get("/portal/status")
def portal_status():
    return {"status": "ok" if not _chaos_mode else "degraded",
            "chaos_mode": _chaos_mode, "synthetic": True}


@app.get("/portal/institution/{code}")
def get_institution(code: str):
    if _chaos_mode and random.random() < _chaos_503_rate:
        raise HTTPException(503, "Service temporarily unavailable (chaos mode)")
    inst = _institutions.get(code)
    if not inst:
        raise HTTPException(404, f"Institution {code} not found")
    return inst


@app.get("/portal/application/{app_id}/intake")
def get_intake(app_id: str):
    if _chaos_mode and random.random() < _chaos_503_rate:
        raise HTTPException(503, "Service temporarily unavailable (chaos mode)")
    approved = random.randint(60, 300)
    actual = approved + random.choice([0, 0, 0, 0, 10, -5, 30])  # Sometimes mismatch
    return PortalIntake(
        application_id=app_id, approved_intake=approved,
        actual_intake=actual, mismatch=(approved != actual),
    )


@app.post("/portal/chaos/on")
def chaos_on():
    global _chaos_mode
    _chaos_mode = True
    return {"chaos_mode": True, "message": "Issuers now returning 503 at 70% rate"}


@app.post("/portal/chaos/off")
def chaos_off():
    global _chaos_mode
    _chaos_mode = False
    return {"chaos_mode": False, "message": "Issuers back to normal"}
