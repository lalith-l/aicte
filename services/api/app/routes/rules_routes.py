"""Rules admin: list, approve (placeholder gate), what-if simulator."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from packages.rules.engine import RulesEngine
from packages.rules.register import RegisterValidationError, load_register, validate_production_readiness
from packages.rules.simulator import WhatIfSimulator
from services.api.app.deps import audit, db, rows_as_dicts
from services.api.app.rbac import require

router = APIRouter()


class ApproveIn(BaseModel):
    approver: str | None = None


class WhatIfIn(BaseModel):
    rule_id: str | None = None
    candidate_clause_ref: str | None = None


def _yaml_rules():
    return load_register()


@router.get("")
@router.get("/")
def list_rules(request: Request, user=require("rules_admin", "sysadmin", "auditor", "scrutiny_officer", "supervisor")):
    yaml_rules = _yaml_rules()
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.id::text, r.code, r.title, r.clause_ref, r.tier, r.severity,
                   rs.status AS ruleset_status, rs.version, r.definition
            FROM rules r JOIN rule_sets rs ON rs.id = r.ruleset_id
            ORDER BY r.code
            """
        )
        db_rules = rows_as_dicts(cur)
    combined = []
    for r in yaml_rules:
        combined.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "clause_ref": r.clause_ref,
                "severity": r.severity,
                "status": r.status,
                "version": r.version,
                "is_placeholder": r.is_placeholder_rule(),
                "conditions": [
                    {"field": c.field, "operator": c.operator.value, "target_value": c.target_value}
                    for c in r.conditions
                ],
            }
        )
    return {"rules": combined, "persisted": db_rules, "synthetic_data": True}


@router.get("/register")
def register_view(user=require("rules_admin", "sysadmin", "auditor")):
    rules = _yaml_rules()
    return {
        "norms": [
            {
                "id": r.id,
                "name": r.name,
                "clause_ref": r.clause_ref,
                "is_placeholder": r.is_placeholder_rule(),
                "status": r.status,
                "severity": r.severity,
            }
            for r in rules
        ],
        "synthetic_data": True,
    }


@router.post("/{rule_id}/approve")
def approve_rule(rule_id: str, body: ApproveIn, request: Request, user=require("rules_admin", "sysadmin")):
    rules = _yaml_rules()
    match = next((r for r in rules if r.id == rule_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Rule not found")
    if match.is_placeholder_rule():
        raise HTTPException(
            status_code=400,
            detail="Rule with PLACEHOLDER clause_ref cannot be approved. A person must fill the handbook clause.",
        )
    try:
        match.status = "ACTIVE"
        validate_production_readiness([match])
    except RegisterValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with db(request, user) as conn:
        audit(conn, user.username, "rule_approved", {"rule_id": rule_id, "synthetic_data": True})
    return {"ok": True, "rule_id": rule_id, "status": "ACTIVE", "synthetic_data": True}


@router.post("/what-if")
def what_if(body: WhatIfIn, request: Request, user=require("rules_admin", "sysadmin")):
    rules = _yaml_rules()
    baseline = RulesEngine(rules)
    candidates = _yaml_rules()
    if body.rule_id and body.candidate_clause_ref:
        for r in candidates:
            if r.id == body.rule_id:
                r.clause_ref = body.candidate_clause_ref
    candidate_engine = RulesEngine(candidates)
    with db(request, user) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id::text, a.institution_id::text,
                   json_agg(json_build_object('field', ef.field, 'value', ef.value)) AS fields
            FROM applications a
            LEFT JOIN documents d ON d.application_id = a.id
            LEFT JOIN extracted_fields ef ON ef.document_id = d.id
            GROUP BY a.id
            LIMIT 400
            """
        )
        apps = []
        for row in cur.fetchall():
            fields = row[2] or []
            apps.append(
                {
                    "id": row[0],
                    "institution_id": row[1],
                    "documents": [{"fields": [f for f in fields if f and f.get("field")]}],
                }
            )
        sim = WhatIfSimulator(baseline, candidate_engine)
        report = sim.simulate(apps, target_rule_id=body.rule_id)
        audit(conn, user.username, "rule_what_if", {"rule_id": body.rule_id, "total": report.total_evaluated})
    return {
        "total_evaluated": report.total_evaluated,
        "baseline_pass_count": report.baseline_pass_count,
        "candidate_pass_count": report.candidate_pass_count,
        "flips_to_pass": report.flips_to_pass,
        "flips_to_deficient": report.flips_to_deficient,
        "flips_to_unknown": report.flips_to_unknown,
        "detailed_flips": [
            {
                "application_id": f.application_id,
                "rule_id": f.rule_id,
                "baseline_status": f.baseline_status,
                "candidate_status": f.candidate_status,
                "reason": f.reason,
            }
            for f in report.detailed_flips[:50]
        ],
        "synthetic_data": True,
        "clause_ref_placeholder": "PLACEHOLDER",
    }
