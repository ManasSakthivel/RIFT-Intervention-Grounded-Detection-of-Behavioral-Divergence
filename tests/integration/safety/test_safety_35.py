"""
Phase 3.5 Safety Adversarial Tests — DATA_MUTATION and ROLLBACK_FAILURE.

Covers the two hard stops that were missing from Phase 3 automated testing.
All 8 hard stops must pass to satisfy Gate 3.5I.

Authority: Phase 3.5 spec §12 (GATE 3.5I — SAFETY CLOSURE)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pytest

from src.rift.safety.safety import (
    HardStopReason,
    SafetyController,
    SafetyDecision,
)


# ─────────────────────────────────────────────────────────────────────────────
# Minimal mock objects (do not depend on InterventionCandidate internals)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MockCandidate:
    service_id: str = "cart"
    mutates_data: bool = False
    intervention_type: str = "NETWORK_LATENCY"


@dataclass
class MockCost:
    blast_radius: float = 0.05
    sla_impact: float = 0.005
    execution_duration_s: float = 30.0


@dataclass
class MockRollbackRecord:
    rollback_attempts: int = 0


def _make_controller() -> SafetyController:
    return SafetyController(
        approved_namespaces=["rift-eval-default"],
        approved_targets={"cart", "frontend", "checkout"},
        t_budget=600.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DATA_MUTATION_ATTEMPT hard stop tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDataMutationHardStop:

    def test_data_mutation_triggers_safe_abort(self):
        sc = _make_controller()
        candidate = MockCandidate(service_id="cart", mutates_data=True)
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0
        )
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.DATA_MUTATION_ATTEMPT

    def test_data_mutation_via_intervention_type(self):
        sc = _make_controller()
        candidate = MockCandidate(service_id="cart", intervention_type="DATA_WRITE")
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0
        )
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.DATA_MUTATION_ATTEMPT

    def test_human_override_cannot_bypass_data_mutation(self):
        """human_override=True must NOT bypass the DATA_MUTATION hard stop."""
        sc = _make_controller()
        candidate = MockCandidate(service_id="cart", mutates_data=True)
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0, human_override=True
        )
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.DATA_MUTATION_ATTEMPT

    def test_non_mutating_candidate_passes_data_check(self):
        """Normal network intervention must NOT trigger DATA_MUTATION."""
        sc = _make_controller()
        candidate = MockCandidate(service_id="cart", mutates_data=False,
                                  intervention_type="NETWORK_LATENCY")
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0
        )
        # Should reach approval, not data-mutation abort
        assert result.hard_stop_reason != HardStopReason.DATA_MUTATION_ATTEMPT


# ─────────────────────────────────────────────────────────────────────────────
# ROLLBACK_FAILURE hard stop tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRollbackFailureHardStop:

    def test_rollback_failure_triggers_safe_abort(self):
        sc = _make_controller()
        result = sc.assess_post_rollback(rollback_succeeded=False)
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.ROLLBACK_FAILURE

    def test_rollback_failure_activates_kill_switch(self):
        """After rollback failure the kill-switch must be set."""
        sc = _make_controller()
        sc.assess_post_rollback(rollback_succeeded=False)
        assert sc._kill_switch_activated is True

    def test_rollback_failure_blocks_subsequent_interventions(self):
        """Any subsequent assess_pre_intervention after rollback failure must SAFE_ABORT."""
        sc = _make_controller()
        sc.assess_post_rollback(rollback_succeeded=False)
        candidate = MockCandidate(service_id="cart")
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0
        )
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.KILL_SWITCH

    def test_human_override_cannot_bypass_rollback_failure(self):
        """human_override=True must NOT allow interventions after rollback failure."""
        sc = _make_controller()
        sc.assess_post_rollback(rollback_succeeded=False)
        candidate = MockCandidate(service_id="cart")
        result = sc.assess_pre_intervention(
            candidate, MockCost(), "rift-eval-default", 0.0, human_override=True
        )
        assert result.decision == SafetyDecision.SAFE_ABORT

    def test_successful_rollback_returns_approved(self):
        """A clean rollback must NOT trigger any hard stop."""
        sc = _make_controller()
        record = MockRollbackRecord(rollback_attempts=1)
        result = sc.assess_post_rollback(rollback_succeeded=True, rollback_record=record)
        assert result.decision == SafetyDecision.APPROVED_AUTONOMOUS
        assert result.hard_stop_reason is None
        assert sc._kill_switch_activated is False

    def test_excessive_rollback_attempts_triggers_abort(self):
        """More than 3 rollback attempts triggers ROLLBACK_FAILURE even if technically True."""
        sc = _make_controller()
        record = MockRollbackRecord(rollback_attempts=4)
        result = sc.assess_post_rollback(rollback_succeeded=True, rollback_record=record)
        assert result.decision == SafetyDecision.SAFE_ABORT
        assert result.hard_stop_reason == HardStopReason.ROLLBACK_FAILURE
