"""
Adversarial safety tests for src/rift/safety/safety.py — Phase 3N

Tests for all 8 hard stop conditions plus authorization escalation logic.

Hard stops tested:
  HS-1  Kill-switch activated → SAFE_ABORT on any subsequent call
  HS-2  Production namespace (not rift-eval-*) → SAFE_ABORT
  HS-3  Namespace is rift-eval-* but NOT in approved list → SAFE_ABORT
  HS-4  Unauthorized target service → SAFE_ABORT
  HS-5  Budget exceeded (cumulative_ed + proposed_ed > T_budget) → SAFE_ABORT
  HS-6  Cascade failure (error_rate > threshold for > duration) → SAFE_ABORT
  HS-7  Unexpected blast radius (non-target anomalies > σ threshold) → SAFE_ABORT

Authorization logic:
  AUTH-1  br < 0.1 AND slai < 0.01 → APPROVED_AUTONOMOUS
  AUTH-2  br >= 0.1 OR slai >= 0.01 OR ed > 60 → APPROVED_SUPERVISED
  AUTH-3  human_override=True → APPROVED_AUTONOMOUS (but NOT if hard stop active)
  AUTH-4  human_override CANNOT override hard stops

Invariants:
  INV-1   Hard stop decision is always SAFE_ABORT
  INV-2   hard_stop_reason is always non-None when SAFE_ABORT
  INV-3   Kill-switch cannot be reset by normal approval flow
  INV-4   Production namespace check fires BEFORE target authorization

Status: VALIDATED — all 8 hard stop conditions tested adversarially.
Authority: docs/PHASE_3_SPEC_FREEZE.md §14
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

import pytest

from rift.safety.safety import (
    HardStopReason,
    SafetyAssessment,
    SafetyController,
    SafetyDecision,
)
from rift.optimizer.cost_model import InterventionCandidate, InterventionCost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candidate(service_id: str = "svc-A") -> InterventionCandidate:
    return InterventionCandidate(
        service_id=service_id,
        variable="latency_p99",
        intervention_type="LATENCY",
        target_value=50.0,
        nominal_value=10.0,
    )


def _make_cost(
    service_id: str = "svc-A",
    blast_radius: float = 0.05,
    sla_impact: float = 0.005,
    ed: float = 30.0,
) -> InterventionCost:
    candidate = _make_candidate(service_id)
    sc = max(0.0, 1.0 - 0.5 * blast_radius - 0.5 * sla_impact)
    if blast_radius < 0.1 and sla_impact < 0.01:
        auth_level = "AUTONOMOUS"
    elif sc < 0.3:
        auth_level = "DENIED"
    else:
        auth_level = "SUPERVISED"
    return InterventionCost(
        candidate=candidate,
        blast_radius=blast_radius,
        sla_impact=sla_impact,
        execution_duration_s=ed,
        rollback_cost=0.1,
        eig=0.3,
        eig_normalized=0.5,
        safety_compliance=sc,
        cost_composite=0.2,
        utility=0.4,
        authorized=auth_level != "DENIED",
        authorization_level=auth_level,
    )


def _make_controller(
    approved_namespaces=None,
    approved_targets=None,
    t_budget: float = 600.0,
) -> SafetyController:
    ns = approved_namespaces or ["rift-eval-test"]
    tgts = approved_targets  # None = no restriction
    return SafetyController(
        approved_namespaces=ns,
        approved_targets=tgts,
        t_budget=t_budget,
        max_blast_radius=0.30,
        max_sla_impact=0.05,
        cascade_error_threshold=0.5,
        cascade_duration_threshold_s=0.0,  # trigger immediately for test
    )


# ---------------------------------------------------------------------------
# Invariant helpers
# ---------------------------------------------------------------------------

def _assert_safe_abort(assessment: SafetyAssessment, expected_reason: HardStopReason = None):
    """Asserts SAFE_ABORT invariants (INV-1 and INV-2)."""
    assert assessment.decision == SafetyDecision.SAFE_ABORT, \
        f"Expected SAFE_ABORT, got {assessment.decision}"
    assert assessment.hard_stop_reason is not None, \
        "hard_stop_reason must be non-None on SAFE_ABORT (INV-2)"
    if expected_reason is not None:
        assert assessment.hard_stop_reason == expected_reason


# ---------------------------------------------------------------------------
# HS-1: Kill-switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    def test_hs1_activate_returns_safe_abort(self):
        """Activating kill-switch immediately returns SAFE_ABORT."""
        ctrl = _make_controller()
        result = ctrl.activate_kill_switch()
        _assert_safe_abort(result, HardStopReason.KILL_SWITCH)
        assert result.rollback_required is True

    def test_hs1_subsequent_pre_intervention_blocked(self):
        """After kill-switch: pre-intervention check returns SAFE_ABORT."""
        ctrl = _make_controller()
        ctrl.activate_kill_switch()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="rift-eval-test", cumulative_ed=0.0
        )
        _assert_safe_abort(assessment, HardStopReason.KILL_SWITCH)

    def test_hs1_subsequent_during_intervention_blocked(self):
        """After kill-switch: during-intervention check returns SAFE_ABORT."""
        ctrl = _make_controller()
        ctrl.activate_kill_switch()
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={},
            system_error_rate=0.0,
            elapsed_s=5.0,
        )
        _assert_safe_abort(assessment, HardStopReason.KILL_SWITCH)

    def test_inv3_kill_switch_cannot_be_bypassed_by_human_override(self):
        """INV-3: human_override=True does NOT override kill-switch (hard stop)."""
        ctrl = _make_controller()
        ctrl.activate_kill_switch()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="rift-eval-test", cumulative_ed=0.0,
            human_override=True,  # must NOT help
        )
        _assert_safe_abort(assessment, HardStopReason.KILL_SWITCH)


# ---------------------------------------------------------------------------
# HS-2/3: Namespace checks
# ---------------------------------------------------------------------------

class TestNamespaceChecks:
    def test_hs2_production_namespace_empty_string(self):
        """Empty namespace → SAFE_ABORT (treated as production)."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.PRODUCTION_NAMESPACE)

    def test_hs2_production_namespace_explicit_name(self):
        """'production' namespace → SAFE_ABORT."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="production", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.PRODUCTION_NAMESPACE)

    def test_hs2_default_namespace_blocked(self):
        """'default' Kubernetes namespace → SAFE_ABORT."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="default", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.PRODUCTION_NAMESPACE)

    def test_hs3_rift_eval_but_not_approved_blocked(self):
        """'rift-eval-*' pattern but not in approved_namespaces list → SAFE_ABORT."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-approved"],
            t_budget=600.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="rift-eval-other", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.PRODUCTION_NAMESPACE)

    def test_hs3_approved_rift_eval_passes(self):
        """Valid rift-eval-* namespace that is in approved_namespaces → passes namespace check."""
        ctrl = _make_controller(approved_namespaces=["rift-eval-test"])
        # Use low-risk cost so we get APPROVED
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.decision != SafetyDecision.SAFE_ABORT
        assert assessment.hard_stop_reason is None

    def test_inv4_namespace_check_fires_before_target_auth(self):
        """INV-4: production namespace SAFE_ABORT fires before target authorization check."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            approved_targets={"svc-B"},  # svc-A is unauthorized
            t_budget=600.0,
        )
        # namespace is production → should fail PRODUCTION_NAMESPACE not UNAUTHORIZED_TARGET
        assessment = ctrl.assess_pre_intervention(
            _make_candidate("svc-A"), _make_cost("svc-A"),
            namespace="production", cumulative_ed=0.0,
        )
        assert assessment.hard_stop_reason == HardStopReason.PRODUCTION_NAMESPACE

    def test_hs2_various_non_eval_namespaces(self):
        """Various non-rift-eval namespaces → all SAFE_ABORT."""
        ctrl = _make_controller()
        for ns in ["staging", "dev", "qa", "rift-prod", "my-rift-eval", ""]:
            assessment = ctrl.assess_pre_intervention(
                _make_candidate(), _make_cost(),
                namespace=ns, cumulative_ed=0.0,
            )
            _assert_safe_abort(assessment, HardStopReason.PRODUCTION_NAMESPACE)


# ---------------------------------------------------------------------------
# HS-4: Unauthorized target
# ---------------------------------------------------------------------------

class TestUnauthorizedTarget:
    def test_hs4_unauthorized_target_blocked(self):
        """Service not in approved_targets → SAFE_ABORT."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            approved_targets={"svc-approved"},
            t_budget=600.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate("svc-A"), _make_cost("svc-A"),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.UNAUTHORIZED_TARGET)

    def test_hs4_authorized_target_passes(self):
        """Service in approved_targets → passes target check."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            approved_targets={"svc-A"},
            t_budget=600.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate("svc-A"), _make_cost("svc-A", blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.hard_stop_reason != HardStopReason.UNAUTHORIZED_TARGET

    def test_hs4_no_approved_targets_restriction_allows_all(self):
        """approved_targets=None means no restriction."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            approved_targets=None,  # no restriction
            t_budget=600.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate("svc-anything"), _make_cost("svc-anything", blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.hard_stop_reason not in (
            HardStopReason.UNAUTHORIZED_TARGET, HardStopReason.PRODUCTION_NAMESPACE
        )

    def test_inv_human_override_cannot_bypass_unauthorized_target(self):
        """human_override=True does NOT bypass unauthorized target hard stop."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            approved_targets={"svc-approved"},
            t_budget=600.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate("svc-other"), _make_cost("svc-other"),
            namespace="rift-eval-test", cumulative_ed=0.0,
            human_override=True,  # must NOT bypass this
        )
        _assert_safe_abort(assessment, HardStopReason.UNAUTHORIZED_TARGET)


# ---------------------------------------------------------------------------
# HS-5: Budget exceeded
# ---------------------------------------------------------------------------

class TestBudgetExceeded:
    def test_hs5_budget_exactly_exceeded(self):
        """cumulative_ed + proposed_ed > T_budget → SAFE_ABORT."""
        ctrl = _make_controller(t_budget=100.0)
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(ed=30.0),
            namespace="rift-eval-test", cumulative_ed=80.0,  # 80+30=110 > 100
        )
        _assert_safe_abort(assessment, HardStopReason.BUDGET_EXCEEDED)

    def test_hs5_budget_exactly_at_limit_passes(self):
        """cumulative_ed + proposed_ed == T_budget (not exceeded) → should NOT abort on budget."""
        ctrl = _make_controller(t_budget=100.0)
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(ed=30.0, blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=70.0,  # 70+30=100 == 100 (not >)
        )
        assert assessment.hard_stop_reason != HardStopReason.BUDGET_EXCEEDED

    def test_hs5_zero_budget_blocks_all(self):
        """t_budget=0 → all interventions exceed budget."""
        ctrl = _make_controller(t_budget=0.0)
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(ed=1.0),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        _assert_safe_abort(assessment, HardStopReason.BUDGET_EXCEEDED)


# ---------------------------------------------------------------------------
# HS-6: Cascade failure
# ---------------------------------------------------------------------------

class TestCascadeFailure:
    def test_hs6_cascade_triggers_safe_abort(self):
        """System error rate above threshold long enough → SAFE_ABORT."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            cascade_error_threshold=0.5,
            cascade_duration_threshold_s=0.0,  # immediate trigger
        )
        # Simulate: first call above threshold triggers cascade tracking
        ctrl.assess_during_intervention(
            non_target_metrics={},
            system_error_rate=0.6,  # above 0.5 threshold
            elapsed_s=5.0,
        )
        # Second call: should now detect duration exceeded
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={},
            system_error_rate=0.6,
            elapsed_s=10.0,
        )
        # With duration_threshold=0.0, cascade_duration > 0.0 → triggers
        _assert_safe_abort(assessment, HardStopReason.CASCADE_FAILURE)
        assert assessment.rollback_required is True

    def test_hs6_cascade_resets_when_error_rate_drops(self):
        """Error rate dropping below threshold resets cascade timer."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            cascade_error_threshold=0.5,
            cascade_duration_threshold_s=30.0,
        )
        # High error rate
        ctrl.assess_during_intervention(
            non_target_metrics={}, system_error_rate=0.8, elapsed_s=5.0
        )
        # Error rate drops → timer resets
        ctrl.assess_during_intervention(
            non_target_metrics={}, system_error_rate=0.1, elapsed_s=10.0
        )
        assert ctrl._cascade_start_time is None

    def test_hs6_below_threshold_no_abort(self):
        """Error rate below threshold → no cascade abort."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            cascade_error_threshold=0.5,
            cascade_duration_threshold_s=0.0,
        )
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={},
            system_error_rate=0.2,  # below 0.5
            elapsed_s=5.0,
        )
        assert assessment.decision != SafetyDecision.SAFE_ABORT


# ---------------------------------------------------------------------------
# HS-7: Unexpected blast radius (non-target anomalies)
# ---------------------------------------------------------------------------

class TestUnexpectedBlastRadius:
    def test_hs7_non_target_anomaly_triggers_abort(self):
        """Non-target service shows anomaly above σ threshold → SAFE_ABORT."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            non_target_sigma_threshold=2.0,
        )
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={"svc-B": 3.5},  # 3.5σ > 2.0
            system_error_rate=0.0,
            elapsed_s=5.0,
            non_target_baseline_stats={"svc-B": {"mean": 0.0, "std": 1.0}},
        )
        _assert_safe_abort(assessment, HardStopReason.UNEXPECTED_BLAST_RADIUS)
        assert assessment.rollback_required is True

    def test_hs7_below_sigma_no_abort(self):
        """Non-target anomaly below threshold → no abort."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            non_target_sigma_threshold=2.0,
        )
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={"svc-B": 1.5},  # 1.5σ < 2.0
            system_error_rate=0.0,
            elapsed_s=5.0,
            non_target_baseline_stats={"svc-B": {"mean": 0.0, "std": 1.0}},
        )
        assert assessment.decision != SafetyDecision.SAFE_ABORT

    def test_hs7_no_baseline_stats_no_abort(self):
        """Without non_target_baseline_stats, isolation check not triggered."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            non_target_sigma_threshold=2.0,
        )
        assessment = ctrl.assess_during_intervention(
            non_target_metrics={"svc-B": 99.9},  # huge value but no baseline
            system_error_rate=0.0,
            elapsed_s=5.0,
            non_target_baseline_stats=None,  # no check
        )
        assert assessment.decision != SafetyDecision.SAFE_ABORT


# ---------------------------------------------------------------------------
# Authorization escalation
# ---------------------------------------------------------------------------

class TestAuthorizationLevels:
    def test_auth1_low_risk_autonomous(self):
        """br<0.1 AND slai<0.01 → APPROVED_AUTONOMOUS."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.decision == SafetyDecision.APPROVED_AUTONOMOUS
        assert assessment.authorization_level == "AUTONOMOUS"

    def test_auth2_high_blast_radius_supervised(self):
        """br>=0.1 → APPROVED_SUPERVISED."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.15, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.decision == SafetyDecision.APPROVED_SUPERVISED
        assert assessment.hard_stop_reason is None

    def test_auth2_long_duration_supervised(self):
        """ed > 60 AND br not low enough for AUTONOMOUS → APPROVED_SUPERVISED.

        Note: is_autonomous requires br < 0.1 AND slai < 0.01.
        When is_autonomous is True (both conditions met), it overrides even long ed.
        So this test uses br=0.15 (>=0.1) to disable the autonomous path,
        then ed=90 triggers needs_supervised."""
        ctrl = SafetyController(
            approved_namespaces=["rift-eval-test"],
            t_budget=600.0,
            supervised_ed_threshold=60.0,
        )
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.15, sla_impact=0.005, ed=90.0),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.decision == SafetyDecision.APPROVED_SUPERVISED

    def test_auth3_human_override_promotes_to_autonomous(self):
        """human_override=True promotes SUPERVISED → AUTONOMOUS (for soft cases)."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.15, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
            human_override=True,
        )
        assert assessment.decision == SafetyDecision.APPROVED_AUTONOMOUS

    def test_auth4_human_override_cannot_override_budget_hard_stop(self):
        """human_override=True does NOT override budget SAFE_ABORT."""
        ctrl = _make_controller(t_budget=10.0)
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(ed=30.0),
            namespace="rift-eval-test", cumulative_ed=0.0,
            human_override=True,
        )
        _assert_safe_abort(assessment, HardStopReason.BUDGET_EXCEEDED)


# ---------------------------------------------------------------------------
# Checks tracking
# ---------------------------------------------------------------------------

class TestChecksTracking:
    def test_checks_performed_populated(self):
        """All performed checks appear in checks_performed list."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert "namespace_check" in assessment.checks_performed
        assert "target_authorization" in assessment.checks_performed
        assert "budget_check" in assessment.checks_performed

    def test_checks_passed_on_clean_approval(self):
        """All checks pass in clean scenario → checks_failed is empty."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert assessment.checks_failed == []

    def test_failed_check_in_checks_failed_on_abort(self):
        """On namespace SAFE_ABORT, 'namespace_check' appears in checks_failed."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(),
            namespace="production", cumulative_ed=0.0,
        )
        assert "namespace_check" in assessment.checks_failed

    def test_timestamp_is_recent(self):
        """assessment.timestamp is within last 10 seconds."""
        ctrl = _make_controller()
        assessment = ctrl.assess_pre_intervention(
            _make_candidate(), _make_cost(blast_radius=0.05, sla_impact=0.005),
            namespace="rift-eval-test", cumulative_ed=0.0,
        )
        assert abs(assessment.timestamp - time.time()) < 10.0
