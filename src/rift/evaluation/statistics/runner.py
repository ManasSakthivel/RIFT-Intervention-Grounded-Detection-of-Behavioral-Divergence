"""RIFT Statistical Evaluation Framework — Phase 3.6 §15.

Re-exports all statistical tests from src/rift/statistics/stats.py under
the evaluation namespace, plus adds the complete confirmatory test runner.

Authority: docs/risk_closure/statistical_plan.md, docs/PHASE_3_SPEC_FREEZE.md §15.
"""
from __future__ import annotations

# Re-export from canonical location
from rift.statistics.stats import (
    HypothesisTestResult,
    cliffs_delta,
    wilcoxon_one_sided,
    tost_equivalence,
    binomial_one_sided,
    holm_bonferroni_correction,
    bh_fdr_correction,
    check_power_achieved,
    run_confirmatory_tests,
)

__all__ = [
    "HypothesisTestResult",
    "cliffs_delta",
    "wilcoxon_one_sided",
    "tost_equivalence",
    "binomial_one_sided",
    "holm_bonferroni_correction",
    "bh_fdr_correction",
    "check_power_achieved",
    "run_confirmatory_tests",
]
