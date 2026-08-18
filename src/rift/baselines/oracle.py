"""Oracle Upper Bound Baseline — Phase 3.6 §12.

Uses known ground-truth causal structure for attribution.
Represents the theoretical maximum performance (upper bound only).

CRITICAL LABELING REQUIREMENT:
  This baseline MUST be labeled "ORACLE UPPER BOUND" in all paper tables,
  figures, and text. It MUST NOT appear in the primary comparison as if it
  were a real deployable baseline.

Authority: docs/baselines/ORACLE.md, Phase 3.6 §12.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext


@dataclass
class OracleGroundTruth:
    """
    Ground-truth information provided exclusively to the Oracle baseline.

    This struct must NEVER be passed to any real baseline (RIFT-FULL,
    RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE). Passing ground truth to a real
    baseline invalidates the comparison.

    The scoring harness logs a WARNING and marks results as INVALID
    if ground truth is accessed outside of OracleUpperBound.run().
    """
    ground_truth_service: str
    ground_truth_fault_type: str
    ground_truth_causal_path: list  # [(source, target), ...]


class OracleUpperBound(BaselineInterface):
    """
    Oracle Upper Bound reference.

    Receives the true root-cause service and returns it with score=1.0.
    This is the maximum achievable Precision@1 for any method.

    Label: ORACLE UPPER BOUND
    NOT a deployable RCA method. Uses privileged ground-truth access.
    """

    def __init__(self, ground_truth: OracleGroundTruth):
        self._gt = ground_truth

    @property
    def baseline_id(self) -> str:
        return "ORACLE-UPPER-BOUND"

    def run(self, context: IncidentContext) -> BaselineOutput:
        """Return ground-truth attribution with perfect confidence."""
        true_service = self._gt.ground_truth_service
        all_services = list(context.metrics.keys())

        # Oracle ranks: true service = 1.0, others = 0.0
        candidates = [(true_service, 1.0)]
        for svc in all_services:
            if svc != true_service:
                candidates.append((svc, 0.0))

        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=candidates[:5],
            abstained=False,
            detection_latency_s=0.0,  # Oracle always detects immediately
            total_intervention_ed_s=0.0,
            notes=(
                "ORACLE UPPER BOUND — uses ground-truth causal structure. "
                "NOT a deployable RCA method. "
                "Must be labeled 'ORACLE UPPER BOUND' in all paper tables. "
                "Must NOT appear in primary comparison as a real baseline. "
                "See docs/baselines/ORACLE.md."
            ),
        )
