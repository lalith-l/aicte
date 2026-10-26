"""Handbook register loader and fail-closed validation guard.

Guards:
1. No rule can be transitioned to 'ACTIVE' if its clause_ref contains 'PLACEHOLDER'.
2. The rules engine refuses startup in production mode if any active rule has unconfigured norms.
3. In prototype/demo mode, rules with 'PLACEHOLDER' evaluate strictly to UNKNOWN
   ("Handbook norm not configured") with a visible PLACEHOLDER badge.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from packages.rules.engine import RuleCondition, RuleDefinition, RuleOperator

from packages.common.paths import RULES_DIR

REGISTER_PATH = RULES_DIR / "register.yaml"


class RegisterValidationError(Exception):
    pass


def load_register(path: Path = REGISTER_PATH) -> list[RuleDefinition]:
    """Load handbook register and convert to RuleDefinition objects."""
    if not path.exists():
        raise FileNotFoundError(f"Register file not found at {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    rules = []
    for item in data.get("norms", []):
        rule_id = item["id"]
        clause_ref = item.get("clause_ref", "PLACEHOLDER")
        severity = item.get("severity", "MUST")

        # Map to standard conditions based on rule ID
        conditions = []
        if rule_id == "R01_land_area_requirement":
            conditions.append(
                RuleCondition(
                    field="land_area_acres",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("min_acres", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R02_built_up_area_requirement":
            conditions.append(
                RuleCondition(
                    field="built_up_area_sqm",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("min_sqm", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R03_affidavit_notary_date":
            # Affidavit date >= stamp paper date
            conditions.append(
                RuleCondition(
                    field="affidavit_date_valid",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R04_faculty_student_ratio":
            conditions.append(
                RuleCondition(
                    field="faculty_ratio",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("cadre_ratio", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R05_trust_deed_purpose":
            conditions.append(
                RuleCondition(
                    field="trust_purpose_valid",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R06_fdr_corpus_fund":
            conditions.append(
                RuleCondition(
                    field="fdr_amount",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("min_amount_inr", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R07_fire_safety_noc_validity":
            conditions.append(
                RuleCondition(
                    field="fire_safety_valid",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R08_state_noc_academic_year":
            conditions.append(
                RuleCondition(
                    field="state_noc_valid",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R09_pan_checksum_validity":
            conditions.append(
                RuleCondition(
                    field="pan_number",
                    operator=RuleOperator.IS_VALID_PAN,
                    target_value="",
                )
            )
        elif rule_id == "R10_intake_portal_conformance":
            conditions.append(
                RuleCondition(
                    field="portal_intake_matches",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R11_required_document_checklist":
            conditions.append(
                RuleCondition(
                    field="required_docs_present",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R12_document_expiry":
            conditions.append(
                RuleCondition(
                    field="validity_days",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("validity_days", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R13_digital_signature_required":
            conditions.append(
                RuleCondition(
                    field="signature_present",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )
        elif rule_id == "R14_name_consistency":
            conditions.append(
                RuleCondition(
                    field="name_match_score",
                    operator=RuleOperator.GREATER_EQUAL,
                    target_value=item.get("parameters", {}).get("name_match_cutoff", "PLACEHOLDER"),
                )
            )
        elif rule_id == "R15_unreadable_scan_unknown":
            conditions.append(
                RuleCondition(
                    field="extractors_agree",
                    operator=RuleOperator.EQUALS,
                    target_value="true",
                )
            )

        rule_def = RuleDefinition(
            id=rule_id,
            name=item["name"],
            description=item.get("description", ""),
            clause_ref=clause_ref,
            severity=severity,
            conditions=conditions,
            status=item.get("status", "DRAFT_PLACEHOLDER"),
        )
        rules.append(rule_def)

    return rules


def validate_production_readiness(rules: list[RuleDefinition]):
    """Fail-closed guard: Disallow production activation of any rule with PLACEHOLDER."""
    offending_rules = []
    for r in rules:
        if r.status == "ACTIVE" and r.is_placeholder_rule():
            offending_rules.append(r.id)

    if offending_rules:
        raise RegisterValidationError(
            f"Cannot activate rules with PLACEHOLDER clause references: {offending_rules}. "
            f"Clause references must be manually filled by a human from the official handbook."
        )
