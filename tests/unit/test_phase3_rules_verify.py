"""Unit tests for Phase 3: Rules engine, Handbook register, What-If simulator, and Debt calculation."""
import pytest
from packages.common.three_valued import Ternary
from packages.rules.engine import (
    RulesEngine,
    RuleDefinition,
    RuleCondition,
    RuleOperator,
)
from packages.rules.register import load_register, validate_production_readiness, RegisterValidationError
from packages.rules.simulator import WhatIfSimulator
from packages.verify.debt import calculate_verification_debt, VerificationStatus
from packages.verify.state_machine import get_next_retry_time, can_transition


def test_placeholder_rule_evaluates_to_unknown():
    """Fail-closed guard: Rule with PLACEHOLDER clause_ref returns UNKNOWN without rejection."""
    rule = RuleDefinition(
        id="R_TEST",
        name="Test Norm",
        description="Test norm with placeholder",
        clause_ref="PLACEHOLDER",
        severity="MUST",
        conditions=[
            RuleCondition(field="area", operator=RuleOperator.GREATER_EQUAL, target_value=5.0)
        ],
    )
    engine = RulesEngine([rule])
    res = engine.evaluate_rule("R_TEST", {"area": 6.0})
    assert res.status == Ternary.UNKNOWN
    assert res.is_placeholder is True
    assert "PLACEHOLDER" in res.reason


def test_active_rule_with_placeholder_fails_production_guard():
    """Cannot activate a rule if clause_ref has PLACEHOLDER."""
    rule = RuleDefinition(
        id="R_BAD",
        name="Bad Rule",
        description="Unreviewed norm",
        clause_ref="PLACEHOLDER",
        severity="MUST",
        status="ACTIVE",
        conditions=[],
    )
    with pytest.raises(RegisterValidationError):
        validate_production_readiness([rule])


def test_rules_register_loads_with_placeholders():
    rules = load_register()
    assert len(rules) >= 10
    # Every rule must have PLACEHOLDER in clause_ref
    for r in rules:
        assert "PLACEHOLDER" in r.clause_ref


def test_what_if_simulator_detects_flips():
    rule_base = RuleDefinition(
        id="R_AREA",
        name="Area Norm",
        description="Norm 5 acres",
        clause_ref="Verified-1.2",
        severity="MUST",
        conditions=[RuleCondition(field="area", operator=RuleOperator.GREATER_EQUAL, target_value=5.0)],
    )
    rule_strict = RuleDefinition(
        id="R_AREA",
        name="Area Norm Strict",
        description="Norm 10 acres",
        clause_ref="Verified-1.2",
        severity="MUST",
        conditions=[RuleCondition(field="area", operator=RuleOperator.GREATER_EQUAL, target_value=10.0)],
    )
    base_engine = RulesEngine([rule_base])
    cand_engine = RulesEngine([rule_strict])

    simulator = WhatIfSimulator(base_engine, cand_engine)
    apps = [
        {"id": "app-1", "documents": [{"fields": [{"field": "area", "value": 7.0}]}]},
        {"id": "app-2", "documents": [{"fields": [{"field": "area", "value": 12.0}]}]},
        {"id": "app-3", "documents": [{"fields": [{"field": "area", "value": 3.0}]}]},
    ]
    report = simulator.simulate(apps, "R_AREA")
    assert report.total_evaluated == 3
    assert report.baseline_pass_count == 2
    assert report.candidate_pass_count == 1
    assert report.flips_to_deficient == 1


def test_verification_debt_calculation():
    docs = [
        {"type_declared": "land_documents", "status": "VERIFIED"},
        {"type_declared": "building_plan", "status": "SOURCE_UNAVAILABLE"},
        {"type_declared": "fire_safety_certificate", "status": "UNVERIFIED"},
    ]
    report = calculate_verification_debt(docs)
    assert report.verified_count == 1
    assert report.unverified_count == 2
    assert report.total_debt > 0.0
    assert report.debt_tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_retry_schedule_backoff():
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    t1 = get_next_retry_time(0, now)
    t2 = get_next_retry_time(1, now)
    assert t1 == now + datetime.timedelta(seconds=60)
    assert t2 == now + datetime.timedelta(seconds=240)
