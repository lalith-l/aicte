"""What-If Simulator for AICTE rule changes.

Replays candidate rulesets over frozen batches of historical/synthetic applications.
Detects:
1. Status flips (APPROVED -> DEFICIENT, DEFICIENT -> APPROVED)
2. Defect yield delta
3. Uncertainty impact (UNKNOWN flips)
4. Affected institution categories and regions

All data is synthetic.
PLACEHOLDER for all handbook clause references.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from packages.common.three_valued import Ternary
from packages.rules.engine import RulesEngine, RuleDefinition


@dataclass
class ApplicationFlip:
    application_id: str
    institution_id: str
    rule_id: str
    baseline_status: str
    candidate_status: str
    reason: str


@dataclass
class SimulationReport:
    total_evaluated: int
    baseline_pass_count: int
    candidate_pass_count: int
    flips_to_pass: int
    flips_to_deficient: int
    flips_to_unknown: int
    detailed_flips: list[ApplicationFlip] = field(default_factory=list)
    synthetic: bool = True
    clause_ref_placeholder: str = "PLACEHOLDER"


class WhatIfSimulator:
    """Executes counterfactual simulation of rules on frozen data."""

    def __init__(self, baseline_engine: RulesEngine, candidate_engine: RulesEngine):
        self.baseline_engine = baseline_engine
        self.candidate_engine = candidate_engine

    def simulate(
        self,
        applications: list[dict[str, Any]],
        target_rule_id: Optional[str] = None,
    ) -> SimulationReport:
        detailed_flips = []
        baseline_pass = 0
        candidate_pass = 0
        flips_to_pass = 0
        flips_to_def = 0
        flips_to_unk = 0

        for app in applications:
            app_id = app.get("id", "unknown")
            inst_id = app.get("institution_id", "unknown")

            # Context from app fields
            context = {}
            for doc in app.get("documents", []):
                for fld in doc.get("fields", []):
                    context[fld.get("field")] = fld.get("value")

            if target_rule_id:
                base_res = self.baseline_engine.evaluate_rule(target_rule_id, context)
                cand_res = self.candidate_engine.evaluate_rule(target_rule_id, context)

                b_status = base_res.status
                c_status = cand_res.status

                if b_status == Ternary.TRUE:
                    baseline_pass += 1
                if c_status == Ternary.TRUE:
                    candidate_pass += 1

                if b_status != c_status:
                    if b_status == Ternary.TRUE and c_status == Ternary.FALSE:
                        flips_to_def += 1
                    elif b_status == Ternary.FALSE and c_status == Ternary.TRUE:
                        flips_to_pass += 1
                    elif c_status == Ternary.UNKNOWN:
                        flips_to_unk += 1

                    detailed_flips.append(
                        ApplicationFlip(
                            application_id=app_id,
                            institution_id=inst_id,
                            rule_id=target_rule_id,
                            baseline_status=b_status.value,
                            candidate_status=c_status.value,
                            reason=f"Baseline: {base_res.reason} -> Candidate: {cand_res.reason}",
                        )
                    )
            else:
                base_results = self.baseline_engine.evaluate_all(context)
                cand_results = self.candidate_engine.evaluate_all(context)

                base_all_true = all(r.status == Ternary.TRUE for r in base_results)
                cand_all_true = all(r.status == Ternary.TRUE for r in cand_results)

                if base_all_true:
                    baseline_pass += 1
                if cand_all_true:
                    candidate_pass += 1

                if base_all_true != cand_all_true:
                    if base_all_true and not cand_all_true:
                        flips_to_def += 1
                    else:
                        flips_to_pass += 1

        return SimulationReport(
            total_evaluated=len(applications),
            baseline_pass_count=baseline_pass,
            candidate_pass_count=candidate_pass,
            flips_to_pass=flips_to_pass,
            flips_to_deficient=flips_to_def,
            flips_to_unknown=flips_to_unk,
            detailed_flips=detailed_flips[:100],  # cap list for performance
        )
