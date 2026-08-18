"""RIFT Intervention Lifecycle — Phase 3.6 §5.

Provides the canonical 7-phase intervention lifecycle interface:
    prepare() → authorize() → apply() → verify() → observe() → rollback() → finalize()

This abstraction wraps the underlying NetworkInterventionEngine and
separates business logic (lifecycle phases) from execution backend
(tc netem vs dry-run vs future backends).

Authority: Phase 3.6 specification §5, docs/PHASE_3_SPEC_FREEZE.md §11, §14.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from src.rift.intervention.network_intervention import (
    NetworkInterventionEngine,
    NetworkInterventionRecord,
    NetworkInterventionStatus,
)
from src.rift.safety.safety import SafetyController, SafetyDecision
from src.rift.optimizer.cost_model import InterventionCandidate, InterventionCost
from src.rift.models.failure_codes import FailureCode, FailureRecord


# ---------------------------------------------------------------------------
# Lifecycle states
# ---------------------------------------------------------------------------

class LifecyclePhase(str, Enum):
    """Ordered phases of a single intervention lifecycle."""
    INITIALIZED = "INITIALIZED"
    PREPARED     = "PREPARED"
    AUTHORIZED   = "AUTHORIZED"
    APPLIED      = "APPLIED"
    VERIFIED     = "VERIFIED"
    OBSERVING    = "OBSERVING"
    ROLLED_BACK  = "ROLLED_BACK"
    FINALIZED    = "FINALIZED"
    ABORTED      = "ABORTED"


# ---------------------------------------------------------------------------
# Lifecycle record
# ---------------------------------------------------------------------------

@dataclass
class InterventionLifecycleRecord:
    """
    Full audit record for one intervention across all 7 lifecycle phases.

    Attaches to RIFTRunRecord.intervention_records for complete provenance.
    """
    lifecycle_id: str
    candidate: InterventionCandidate
    phase: LifecyclePhase = LifecyclePhase.INITIALIZED
    authorized: bool = False
    authorization_level: str = "PENDING"
    applied: bool = False
    verified: bool = False
    rolled_back: bool = False
    finalized: bool = False
    failure_codes: List[FailureCode] = field(default_factory=list)
    # Timestamps per phase
    t_prepare: Optional[float] = None
    t_authorize: Optional[float] = None
    t_apply: Optional[float] = None
    t_verify: Optional[float] = None
    t_observe_start: Optional[float] = None
    t_observe_end: Optional[float] = None
    t_rollback: Optional[float] = None
    t_finalize: Optional[float] = None
    # Underlying network record reference
    network_record_id: Optional[str] = None
    # Observation data collected during OBSERVING phase
    post_observation_summary: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def add_failure(self, code: FailureCode, detail: str = "") -> None:
        if code not in self.failure_codes:
            self.failure_codes.append(code)
        if detail:
            sep = "; " if self.notes else ""
            self.notes = self.notes + sep + detail

    def to_dict(self) -> dict:
        return {
            "lifecycle_id": self.lifecycle_id,
            "candidate_service": self.candidate.service_id,
            "candidate_variable": self.candidate.variable,
            "intervention_type": self.candidate.intervention_type,
            "phase": self.phase.value,
            "authorized": self.authorized,
            "authorization_level": self.authorization_level,
            "applied": self.applied,
            "verified": self.verified,
            "rolled_back": self.rolled_back,
            "finalized": self.finalized,
            "failure_codes": [c.value for c in self.failure_codes],
            "network_record_id": self.network_record_id,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Lifecycle manager
# ---------------------------------------------------------------------------

class InterventionLifecycle:
    """
    Manages a single intervention through all 7 lifecycle phases.

    Usage:
        lc = InterventionLifecycle(candidate, cost, engine, safety, namespace)
        if lc.prepare() and lc.authorize(cumulative_ed):
            lc.apply()
            lc.verify()
            lc.observe(collect_fn, duration_s=30.0)
        lc.rollback()
        lc.finalize()
        record = lc.record

    The lifecycle is strictly sequential. Phases must be called in order.
    rollback() may be called from any phase; it is always safe.
    """

    def __init__(
        self,
        candidate: InterventionCandidate,
        cost: InterventionCost,
        engine: NetworkInterventionEngine,
        safety: SafetyController,
        namespace: str,
        cumulative_ed_s: float = 0.0,
        dry_run: bool = True,
    ):
        self.candidate = candidate
        self.cost = cost
        self.engine = engine
        self.safety = safety
        self.namespace = namespace
        self.cumulative_ed_s = cumulative_ed_s
        self.dry_run = dry_run

        self.record = InterventionLifecycleRecord(
            lifecycle_id=str(uuid.uuid4()),
            candidate=candidate,
        )
        self._net_record: Optional[NetworkInterventionRecord] = None

    # ------------------------------------------------------------------
    # Phase 1: prepare
    # ------------------------------------------------------------------

    def prepare(self) -> bool:
        """
        PREPARE: Validate intervention parameters before any system modification.

        Checks:
        - Target service is non-empty
        - Intervention type is supported
        - Nominal and target values are finite

        Returns True if preparation succeeded.
        """
        self.record.t_prepare = time.time()

        issues = []
        if not self.candidate.service_id.strip():
            issues.append("service_id is empty")
        if not self.candidate.intervention_type.strip():
            issues.append("intervention_type is empty")
        if not np.isfinite(self.candidate.target_value):
            issues.append(f"target_value {self.candidate.target_value} is not finite")
        if not np.isfinite(self.candidate.nominal_value):
            issues.append(f"nominal_value {self.candidate.nominal_value} is not finite")

        if issues:
            self.record.phase = LifecyclePhase.ABORTED
            self.record.add_failure(
                FailureCode.INTERVENTION_FAILURE,
                f"prepare() failed: {'; '.join(issues)}"
            )
            return False

        self.record.phase = LifecyclePhase.PREPARED
        return True

    # ------------------------------------------------------------------
    # Phase 2: authorize
    # ------------------------------------------------------------------

    def authorize(self, cumulative_ed: Optional[float] = None) -> bool:
        """
        AUTHORIZE: Run the safety pre-intervention gate.

        Returns True if APPROVED_AUTONOMOUS or APPROVED_SUPERVISED.
        Returns False (and sets phase=ABORTED) for DENIED or SAFE_ABORT.

        Hard stops are enforced regardless of human_override.
        """
        if self.record.phase not in (LifecyclePhase.PREPARED,):
            return False

        self.record.t_authorize = time.time()
        ed = cumulative_ed if cumulative_ed is not None else self.cumulative_ed_s

        assessment = self.safety.assess_pre_intervention(
            candidate=self.candidate,
            cost=self.cost,
            namespace=self.namespace,
            cumulative_ed=ed,
        )

        self.record.authorization_level = assessment.authorization_level

        if assessment.decision in (SafetyDecision.APPROVED_AUTONOMOUS,
                                   SafetyDecision.APPROVED_SUPERVISED):
            self.record.authorized = True
            self.record.phase = LifecyclePhase.AUTHORIZED
            return True

        # DENIED or SAFE_ABORT
        self.record.authorized = False
        self.record.phase = LifecyclePhase.ABORTED
        self.record.add_failure(
            FailureCode.SAFETY_ABORT,
            f"authorize() hard-stop: {assessment.hard_stop_reason} "
            f"({assessment.notes})"
        )
        return False

    # ------------------------------------------------------------------
    # Phase 3: apply
    # ------------------------------------------------------------------

    def apply(self) -> bool:
        """
        APPLY: Execute the tc netem command (or dry-run log).

        Only callable after successful authorize().
        Returns True if the apply command succeeded.
        """
        if self.record.phase != LifecyclePhase.AUTHORIZED:
            return False

        self.record.t_apply = time.time()

        # Build NetworkInterventionRecord from candidate
        iface = "eth0"
        dest_ip = "0.0.0.0"  # to be resolved from service discovery in live execution
        lat_ms = (
            self.candidate.target_value
            if self.candidate.intervention_type in ("LATENCY",)
            else 0.0
        )
        loss_pct = (
            self.candidate.target_value
            if self.candidate.intervention_type in ("PACKET_LOSS",)
            else 0.0
        )

        self._net_record = NetworkInterventionRecord(
            record_id=str(uuid.uuid4()),
            source_service=self.namespace,
            destination_service=self.candidate.service_id,
            destination_ip=dest_ip,
            interface=iface,
            latency_ms=lat_ms,
            jitter_ms=lat_ms * 0.1,  # 10% jitter
            packet_loss_pct=loss_pct,
            tc_handle="10:",
            tc_parent="1:",
        )

        applied = self.engine.apply(self._net_record)
        self.record.network_record_id = applied.record_id

        if applied.status in (NetworkInterventionStatus.APPLIED,):
            self.record.applied = True
            self.record.phase = LifecyclePhase.APPLIED
            return True

        # dry_run returns APPLIED too via NetworkInterventionEngine
        if self.dry_run:
            self.record.applied = True
            self.record.phase = LifecyclePhase.APPLIED
            return True

        self.record.phase = LifecyclePhase.ABORTED
        self.record.add_failure(
            FailureCode.INTERVENTION_FAILURE,
            f"apply() failed: tc command returned non-zero. {applied.notes}"
        )
        return False

    # ------------------------------------------------------------------
    # Phase 4: verify
    # ------------------------------------------------------------------

    def verify(self, measured_latency_ms: Optional[float] = None) -> bool:
        """
        VERIFY: Independently confirm the intervention is measurably active.

        In dry-run mode: returns True but marks as DRY_RUN (not confirmed).
        In live mode: requires independent ping/tc measurement.

        Returns True if verified (or dry_run).
        Returns False if independent measurement shows intervention not active.
        """
        if self.record.phase != LifecyclePhase.APPLIED:
            return False

        self.record.t_verify = time.time()

        if self._net_record is None:
            self.record.add_failure(
                FailureCode.INTERVENTION_NOT_VERIFIED,
                "verify(): no network record available"
            )
            return False

        verified_record = self.engine.verify(self._net_record, measured_latency_ms)

        if verified_record.status == NetworkInterventionStatus.VERIFIED:
            self.record.verified = True
            self.record.phase = LifecyclePhase.VERIFIED
            return True

        if self.dry_run:
            # Dry-run: cannot verify, but not a failure — mark explicitly
            self.record.verified = False
            self.record.phase = LifecyclePhase.VERIFIED
            self.record.notes = (
                (self.record.notes + "; " if self.record.notes else "") +
                "DRY_RUN: verify() skipped — measurement not performed."
            )
            return True  # allow pipeline to continue in dry-run

        self.record.phase = LifecyclePhase.ABORTED
        self.record.add_failure(
            FailureCode.INTERVENTION_NOT_VERIFIED,
            f"verify() failed: independent measurement did not confirm intervention. "
            f"{verified_record.notes}"
        )
        return False

    # ------------------------------------------------------------------
    # Phase 5: observe
    # ------------------------------------------------------------------

    def observe(
        self,
        collect_fn,
        duration_s: float = 30.0,
    ) -> Dict[str, Any]:
        """
        OBSERVE: Collect post-intervention metrics for duration_s seconds.

        collect_fn: callable(services: List[str], window_s: float) → dict
            Expected to return {service_id: DataFrame(time, value)} or equivalent.

        Returns the collected observation summary.
        Records timestamps for CID computation.
        """
        if self.record.phase not in (LifecyclePhase.VERIFIED,):
            return {}

        self.record.t_observe_start = time.time()

        try:
            services = [self.candidate.service_id]
            observations = collect_fn(services=services, window_s=duration_s)
        except Exception as exc:
            self.record.add_failure(
                FailureCode.TELEMETRY_FAILURE,
                f"observe() collection failed: {exc}"
            )
            observations = {}

        self.record.t_observe_end = time.time()
        self.record.post_observation_summary = {
            "duration_s": duration_s,
            "services_observed": list(observations.keys()),
            "n_series": len(observations),
        }
        self.record.phase = LifecyclePhase.OBSERVING
        return observations

    # ------------------------------------------------------------------
    # Phase 6: rollback
    # ------------------------------------------------------------------

    def rollback(self) -> bool:
        """
        ROLLBACK: Remove the tc netem rule and restore baseline traffic.

        Must always be called — even after failure at earlier phases.
        Returns True if rollback succeeded or if there was nothing to roll back.
        """
        self.record.t_rollback = time.time()

        if self._net_record is None:
            # Nothing was applied; nothing to roll back
            self.record.rolled_back = True
            self.record.phase = LifecyclePhase.ROLLED_BACK
            return True

        rolled = self.engine.rollback(self._net_record)
        success = rolled.status == NetworkInterventionStatus.ROLLED_BACK

        if success or self.dry_run:
            self.record.rolled_back = True
            self.record.phase = LifecyclePhase.ROLLED_BACK
            return True

        # Rollback failed — this is a safety-critical state
        self.record.add_failure(
            FailureCode.SAFETY_ABORT,
            "rollback() failed. tc netem rule may still be active. "
            "Safety controller must be consulted. Operator action required."
        )
        self.record.phase = LifecyclePhase.ABORTED
        return False

    # ------------------------------------------------------------------
    # Phase 7: finalize
    # ------------------------------------------------------------------

    def finalize(self) -> InterventionLifecycleRecord:
        """
        FINALIZE: Mark the lifecycle complete and return the full record.

        Validates that rollback was performed before finalizing.
        Returns the InterventionLifecycleRecord for attachment to RIFTRunRecord.
        """
        self.record.t_finalize = time.time()

        if not self.record.rolled_back:
            self.record.add_failure(
                FailureCode.INTERVENTION_FAILURE,
                "finalize() called before rollback(). "
                "Rollback must always be performed before finalizing."
            )

        if self.record.phase not in (LifecyclePhase.ABORTED,):
            self.record.phase = LifecyclePhase.FINALIZED
        self.record.finalized = True
        return self.record
