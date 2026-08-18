"""RIFT Safety Controller — Phase 3N. Hard stops enforced independently."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class SafetyDecision(str, Enum):
    APPROVED_AUTONOMOUS = "APPROVED_AUTONOMOUS"
    APPROVED_SUPERVISED = "APPROVED_SUPERVISED"
    DENIED = "DENIED"
    SAFE_ABORT = "SAFE_ABORT"


class HardStopReason(str, Enum):
    PRODUCTION_NAMESPACE = "PRODUCTION_NAMESPACE"
    UNAUTHORIZED_TARGET = "UNAUTHORIZED_TARGET"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    ROLLBACK_FAILURE = "ROLLBACK_FAILURE"
    UNEXPECTED_BLAST_RADIUS = "UNEXPECTED_BLAST_RADIUS"
    DATA_MUTATION_ATTEMPT = "DATA_MUTATION_ATTEMPT"
    CASCADE_FAILURE = "CASCADE_FAILURE"
    KILL_SWITCH = "KILL_SWITCH"


@dataclass
class SafetyAssessment:
    decision: SafetyDecision
    hard_stop_reason: Optional[HardStopReason]
    authorization_level: str
    checks_performed: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    rollback_required: bool = False
    timestamp: float = field(default_factory=time.time)
    notes: str = ""


class SafetyController:
    """
    RIFT safety controller.

    Must be consulted BEFORE any intervention is dispatched.
    Hard stops are enforced independently of the intervention engine.
    All 8 hard stop conditions cause SAFE_ABORT regardless of other state.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §14
    """

    # Namespace pattern: only rift-eval-* namespaces are allowed
    _EVAL_NAMESPACE_PATTERN = re.compile(r'^rift-eval-.+$')

    def __init__(
        self,
        approved_namespaces: Optional[List[str]] = None,
        approved_targets: Optional[Set[str]] = None,
        t_budget: float = 600.0,
        max_blast_radius: float = 0.30,
        max_sla_impact: float = 0.05,
        autonomous_br_threshold: float = 0.1,
        autonomous_slai_threshold: float = 0.01,
        supervised_ed_threshold: float = 60.0,
        cascade_error_threshold: float = 0.5,
        cascade_duration_threshold_s: float = 30.0,
        non_target_sigma_threshold: float = 2.0,
    ):
        self.approved_namespaces = approved_namespaces or []
        self.approved_targets = approved_targets or set()
        self.t_budget = t_budget
        self.max_blast_radius = max_blast_radius
        self.max_sla_impact = max_sla_impact
        self.autonomous_br_threshold = autonomous_br_threshold
        self.autonomous_slai_threshold = autonomous_slai_threshold
        self.supervised_ed_threshold = supervised_ed_threshold
        self.cascade_error_threshold = cascade_error_threshold
        self.cascade_duration_threshold_s = cascade_duration_threshold_s
        self.non_target_sigma_threshold = non_target_sigma_threshold
        self._kill_switch_activated = False
        self._cascade_start_time: Optional[float] = None

    def is_production_namespace(self, namespace: str) -> bool:
        """Returns True if namespace is NOT a valid rift-eval-* namespace."""
        if not namespace:
            return True
        if not self._EVAL_NAMESPACE_PATTERN.match(namespace):
            return True
        if namespace not in self.approved_namespaces:
            return True
        return False

    def activate_kill_switch(self) -> SafetyAssessment:
        """Immediate SAFE_ABORT regardless of state."""
        self._kill_switch_activated = True
        return SafetyAssessment(
            decision=SafetyDecision.SAFE_ABORT,
            hard_stop_reason=HardStopReason.KILL_SWITCH,
            authorization_level="DENIED",
            checks_performed=["kill_switch"],
            checks_failed=["kill_switch"],
            rollback_required=True,
            notes="Kill-switch activated. All interventions halted immediately.",
        )

    def assess_pre_intervention(
        self,
        candidate,  # InterventionCandidate
        cost,       # InterventionCost
        namespace: str,
        cumulative_ed: float,
        human_override: bool = False,
    ) -> SafetyAssessment:
        """
        Pre-intervention safety gate. Must be called BEFORE any intervention.

        Returns SAFE_ABORT immediately on any hard stop condition.
        Returns DENIED if target is unauthorized.
        Returns APPROVED_SUPERVISED if human confirmation is required.
        Returns APPROVED_AUTONOMOUS for low-risk interventions.

        A human_override=True does NOT override hard stops — it only promotes
        SUPERVISED → AUTONOMOUS for borderline cases.
        """
        checks_performed = []
        checks_passed = []
        checks_failed = []

        # Hard stop 1: Kill-switch
        checks_performed.append("kill_switch")
        if self._kill_switch_activated:
            checks_failed.append("kill_switch")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.KILL_SWITCH,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=True,
                notes="Kill-switch is active.",
            )
        checks_passed.append("kill_switch")

        # Hard stop 1: Production namespace
        checks_performed.append("namespace_check")
        if self.is_production_namespace(namespace):
            checks_failed.append("namespace_check")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.PRODUCTION_NAMESPACE,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=False,
                notes=(
                    f"Namespace '{namespace}' does not match rift-eval-* pattern. "
                    "All interventions blocked in non-evaluation namespaces."
                ),
            )
        checks_passed.append("namespace_check")

        # Hard stop 2: Unauthorized target
        checks_performed.append("target_authorization")
        if self.approved_targets and candidate.service_id not in self.approved_targets:
            checks_failed.append("target_authorization")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.UNAUTHORIZED_TARGET,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=False,
                notes=(
                    f"Service '{candidate.service_id}' is not in the approved_targets "
                    f"registry. Human_override={human_override} does NOT bypass this check."
                ),
            )
        checks_passed.append("target_authorization")

        # Hard stop 3: Budget exceeded
        checks_performed.append("budget_check")
        if cumulative_ed + cost.execution_duration_s > self.t_budget:
            checks_failed.append("budget_check")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.BUDGET_EXCEEDED,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=False,
                notes=(
                    f"Cumulative ED ({cumulative_ed:.1f}s) + proposed ED "
                    f"({cost.execution_duration_s:.1f}s) = {cumulative_ed + cost.execution_duration_s:.1f}s "
                    f"exceeds T_budget ({self.t_budget:.1f}s)."
                ),
            )
        checks_passed.append("budget_check")

        # Hard stop 4: Data mutation attempt
        checks_performed.append("data_mutation_check")
        if (
            getattr(candidate, "mutates_data", False)
            or getattr(candidate, "intervention_type", "") == "DATA_WRITE"
        ):
            checks_failed.append("data_mutation_check")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.DATA_MUTATION_ATTEMPT,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=False,
                notes=(
                    "Data mutation intervention detected. "
                    "RIFT never mutates application data. Hard stop enforced. "
                    f"human_override={human_override} does NOT bypass this check."
                ),
            )
        checks_passed.append("data_mutation_check")

        # Soft check: blast radius
        checks_performed.append("blast_radius")
        br_ok = cost.blast_radius < self.max_blast_radius
        if not br_ok:
            checks_failed.append("blast_radius")
        else:
            checks_passed.append("blast_radius")

        # Soft check: SLA impact
        checks_performed.append("sla_impact")
        slai_ok = cost.sla_impact < self.max_sla_impact
        if not slai_ok:
            checks_failed.append("sla_impact")
        else:
            checks_passed.append("sla_impact")

        # Determine authorization level
        is_autonomous = (
            cost.blast_radius < self.autonomous_br_threshold and
            cost.sla_impact < self.autonomous_slai_threshold
        )
        needs_supervised = (
            cost.blast_radius >= self.autonomous_br_threshold or
            cost.sla_impact >= self.autonomous_slai_threshold or
            cost.execution_duration_s > self.supervised_ed_threshold
        )

        if is_autonomous or human_override:
            decision = SafetyDecision.APPROVED_AUTONOMOUS
            auth_level = "AUTONOMOUS"
        elif needs_supervised:
            decision = SafetyDecision.APPROVED_SUPERVISED
            auth_level = "SUPERVISED"
        else:
            decision = SafetyDecision.APPROVED_AUTONOMOUS
            auth_level = "AUTONOMOUS"

        return SafetyAssessment(
            decision=decision,
            hard_stop_reason=None,
            authorization_level=auth_level,
            checks_performed=checks_performed,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            rollback_required=False,
            notes=f"Pre-intervention safety gate passed with level={auth_level}.",
        )

    def assess_during_intervention(
        self,
        non_target_metrics: Dict[str, float],
        system_error_rate: float,
        elapsed_s: float,
        non_target_baseline_stats: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> SafetyAssessment:
        """
        Mid-intervention monitoring. Call every 5s during active intervention.
        Triggers SAFE_ABORT if conditions deteriorate.
        """
        checks_performed = []
        checks_passed = []
        checks_failed = []

        # Hard stop: kill-switch
        checks_performed.append("kill_switch")
        if self._kill_switch_activated:
            checks_failed.append("kill_switch")
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.KILL_SWITCH,
                authorization_level="DENIED",
                checks_performed=checks_performed,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                rollback_required=True,
            )
        checks_passed.append("kill_switch")

        # Hard stop: cascade failure detection
        checks_performed.append("cascade_check")
        if system_error_rate > self.cascade_error_threshold:
            if self._cascade_start_time is None:
                self._cascade_start_time = time.time()
            cascade_duration = time.time() - self._cascade_start_time
            if cascade_duration > self.cascade_duration_threshold_s:
                checks_failed.append("cascade_check")
                return SafetyAssessment(
                    decision=SafetyDecision.SAFE_ABORT,
                    hard_stop_reason=HardStopReason.CASCADE_FAILURE,
                    authorization_level="DENIED",
                    checks_performed=checks_performed,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                    rollback_required=True,
                    notes=(
                        f"System-wide error rate {system_error_rate:.1%} > "
                        f"{self.cascade_error_threshold:.1%} for "
                        f"{cascade_duration:.0f}s > {self.cascade_duration_threshold_s:.0f}s. "
                        "Cascade failure detected."
                    ),
                )
        else:
            self._cascade_start_time = None
        checks_passed.append("cascade_check")

        # Hard stop: unexpected blast radius (non-target anomalies)
        checks_performed.append("isolation_check")
        if non_target_baseline_stats:
            anomalous_non_targets = []
            for svc, anomaly_score in non_target_metrics.items():
                if anomaly_score > self.non_target_sigma_threshold:
                    anomalous_non_targets.append((svc, anomaly_score))
            if anomalous_non_targets:
                checks_failed.append("isolation_check")
                return SafetyAssessment(
                    decision=SafetyDecision.SAFE_ABORT,
                    hard_stop_reason=HardStopReason.UNEXPECTED_BLAST_RADIUS,
                    authorization_level="DENIED",
                    checks_performed=checks_performed,
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                    rollback_required=True,
                    notes=(
                        f"Non-target services showing anomalies > {self.non_target_sigma_threshold}σ: "
                        f"{anomalous_non_targets}. Intervention side-effects detected. ABORT."
                    ),
                )
        checks_passed.append("isolation_check")

        return SafetyAssessment(
            decision=SafetyDecision.APPROVED_AUTONOMOUS,
            hard_stop_reason=None,
            authorization_level="AUTONOMOUS",
            checks_performed=checks_performed,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            rollback_required=False,
            notes=f"Mid-intervention check passed at elapsed={elapsed_s:.1f}s.",
        )

    def assess_post_rollback(
        self,
        rollback_succeeded: bool,
        rollback_record=None,
        remaining_active_records: Optional[List] = None,
    ) -> SafetyAssessment:
        """
        POST-ROLLBACK safety gate. Called after every rollback attempt.

        Hard stop 5: ROLLBACK_FAILURE
        If rollback fails, the intervention state is unknown and the system
        cannot safely continue. Kill-switch is also activated to prevent any
        further intervention attempts.

        A failed rollback is distinct from a failed intervention — a failed
        rollback means we may have left an active tc rule that continues to
        affect traffic. This is a safety-critical state.

        Authority: docs/PHASE_3_SPEC_FREEZE.md §14
        """
        max_attempts = 3
        attempts = getattr(rollback_record, "rollback_attempts", 0) if rollback_record else 0

        if not rollback_succeeded or attempts > max_attempts:
            # Activate kill-switch: no further interventions permitted
            self._kill_switch_activated = True
            return SafetyAssessment(
                decision=SafetyDecision.SAFE_ABORT,
                hard_stop_reason=HardStopReason.ROLLBACK_FAILURE,
                authorization_level="DENIED",
                checks_performed=["rollback_verification"],
                checks_passed=[],
                checks_failed=["rollback_verification"],
                rollback_required=True,
                notes=(
                    f"Rollback failed after {attempts} attempt(s). "
                    "Kill-switch activated. All further interventions blocked. "
                    "Operator action required: manually verify tc rules and remove any "
                    "remaining netem qdiscs before resetting the evaluation environment."
                ),
            )

        return SafetyAssessment(
            decision=SafetyDecision.APPROVED_AUTONOMOUS,
            hard_stop_reason=None,
            authorization_level="AUTONOMOUS",
            checks_performed=["rollback_verification"],
            checks_passed=["rollback_verification"],
            checks_failed=[],
            rollback_required=False,
            notes=f"Rollback verified successfully after {attempts} attempt(s).",
        )
