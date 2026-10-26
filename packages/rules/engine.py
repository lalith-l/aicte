"""Three-valued rules engine for AICTE applications.

Core principles:
1. Kleene logic: TRUE, FALSE, UNKNOWN.
2. UNKNOWN never triggers an automatic rejection or mismatch.
3. Closed operator set: EQUALS, NOT_EQUALS, GT, LT, GTE, LTE, IN, CONTAINS,
   EXISTS, IS_VALID_DATE, IS_VALID_PAN, MATCHES_PORTAL.
4. Lineage tracking: Every rule evaluation records field dependency lineage.
5. Fail-closed placeholder guard:
   Any rule where clause_ref == 'PLACEHOLDER' or minimums == 'PLACEHOLDER'
   evaluates to UNKNOWN ('Handbook norm not configured').
   Authority rule: deterministic findings only written when status is definitive.

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from packages.common.three_valued import Ternary, ThreeValued


class RuleOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_EQUAL = "GREATER_EQUAL"
    LESS_EQUAL = "LESS_EQUAL"
    IN = "IN"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"
    IS_VALID_DATE = "IS_VALID_DATE"
    IS_VALID_PAN = "IS_VALID_PAN"
    MATCHES_PORTAL = "MATCHES_PORTAL"


@dataclass
class RuleCondition:
    field: str
    operator: RuleOperator
    target_value: Any
    doc_type: Optional[str] = None


@dataclass
class RuleEvaluationResult:
    rule_id: str
    rule_name: str
    clause_ref: str
    status: Ternary
    reason: str
    lineage_fields: list[str] = field(default_factory=list)
    measured_value: Any = None
    target_value: Any = None
    is_placeholder: bool = False
    synthetic: bool = True


@dataclass
class RuleDefinition:
    id: str
    name: str
    description: str
    clause_ref: str  # Must be 'PLACEHOLDER' or human-filled
    severity: str    # MUST, SHOULD, COULD
    conditions: list[RuleCondition]
    status: str = "DRAFT"  # DRAFT, ACTIVE, RETIRED
    version: str = "1.0.0"

    def is_placeholder_rule(self) -> bool:
        if self.clause_ref == "PLACEHOLDER" or "PLACEHOLDER" in str(self.clause_ref):
            return True
        for cond in self.conditions:
            if cond.target_value == "PLACEHOLDER" or "PLACEHOLDER" in str(cond.target_value):
                return True
        return False


def _evaluate_condition(cond: RuleCondition, value: Any) -> Ternary:
    if value is None:
        if cond.operator == RuleOperator.EXISTS:
            return Ternary.FALSE
        return Ternary.UNKNOWN

    if cond.operator == RuleOperator.EXISTS:
        return Ternary.TRUE if value else Ternary.FALSE

    # Check if target is placeholder
    if cond.target_value == "PLACEHOLDER" or "PLACEHOLDER" in str(cond.target_value):
        return Ternary.UNKNOWN

    try:
        if cond.operator == RuleOperator.EQUALS:
            return Ternary.TRUE if str(value).strip().lower() == str(cond.target_value).strip().lower() else Ternary.FALSE

        elif cond.operator == RuleOperator.NOT_EQUALS:
            return Ternary.TRUE if str(value).strip().lower() != str(cond.target_value).strip().lower() else Ternary.FALSE

        elif cond.operator == RuleOperator.GREATER_THAN:
            return Ternary.TRUE if float(value) > float(cond.target_value) else Ternary.FALSE

        elif cond.operator == RuleOperator.GREATER_EQUAL:
            return Ternary.TRUE if float(value) >= float(cond.target_value) else Ternary.FALSE

        elif cond.operator == RuleOperator.LESS_THAN:
            return Ternary.TRUE if float(value) < float(cond.target_value) else Ternary.FALSE

        elif cond.operator == RuleOperator.LESS_EQUAL:
            return Ternary.TRUE if float(value) <= float(cond.target_value) else Ternary.FALSE

        elif cond.operator == RuleOperator.IN:
            targets = [str(t).strip().lower() for t in cond.target_value] if isinstance(cond.target_value, list) else [str(cond.target_value).strip().lower()]
            return Ternary.TRUE if str(value).strip().lower() in targets else Ternary.FALSE

        elif cond.operator == RuleOperator.CONTAINS:
            return Ternary.TRUE if str(cond.target_value).strip().lower() in str(value).strip().lower() else Ternary.FALSE

        elif cond.operator == RuleOperator.IS_VALID_PAN:
            pan_regex = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
            if re.match(pan_regex, str(value)):
                return Ternary.TRUE
            return Ternary.FALSE

        elif cond.operator == RuleOperator.IS_VALID_DATE:
            try:
                datetime.date.fromisoformat(str(value))
                return Ternary.TRUE
            except ValueError:
                return Ternary.FALSE

        elif cond.operator == RuleOperator.MATCHES_PORTAL:
            # Matches against external portal dict
            return Ternary.TRUE if str(value) == str(cond.target_value) else Ternary.FALSE

    except (ValueError, TypeError):
        return Ternary.UNKNOWN

    return Ternary.UNKNOWN


class RulesEngine:
    """Evaluates rulesets against application data under Three-Valued Logic."""

    def __init__(self, rules: list[RuleDefinition] = None):
        self.rules: dict[str, RuleDefinition] = {r.id: r for r in (rules or [])}

    def register_rule(self, rule: RuleDefinition):
        self.rules[rule.id] = rule

    def evaluate_rule(self, rule_id: str, context: dict[str, Any]) -> RuleEvaluationResult:
        rule = self.rules.get(rule_id)
        if not rule:
            return RuleEvaluationResult(
                rule_id=rule_id,
                rule_name="Unknown Rule",
                clause_ref="PLACEHOLDER",
                status=Ternary.UNKNOWN,
                reason="Rule not found in registry",
            )

        # Fail-closed guard on PLACEHOLDER clause references
        if rule.is_placeholder_rule():
            return RuleEvaluationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                clause_ref=rule.clause_ref,
                status=Ternary.UNKNOWN,
                reason="Handbook norm not configured (PLACEHOLDER clause reference or parameter). Awaiting human handbook review.",
                is_placeholder=True,
                lineage_fields=[c.field for c in rule.conditions],
            )

        # Evaluate conditions under Kleene conjunction (all_of)
        condition_results = []
        lineage = []
        measured = {}

        for cond in rule.conditions:
            val = context.get(cond.field)
            res = _evaluate_condition(cond, val)
            condition_results.append(res)
            lineage.append(cond.field)
            measured[cond.field] = val

        overall_status = Ternary.all_of(condition_results)

        reason = "All rule conditions satisfied" if overall_status == Ternary.TRUE else (
            "Condition failed" if overall_status == Ternary.FALSE else "Insufficient data or unverified dependency (evaluates to UNKNOWN without rejection)"
        )

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            clause_ref=rule.clause_ref,
            status=overall_status,
            reason=reason,
            lineage_fields=lineage,
            measured_value=measured,
            is_placeholder=False,
        )

    def evaluate_all(self, context: dict[str, Any]) -> list[RuleEvaluationResult]:
        return [self.evaluate_rule(rid, context) for rid in sorted(self.rules.keys())]
