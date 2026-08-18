"""Sage+Chaos Baseline Stub — Phase 3.6 §11.

Status: DEFERRED_TO_PHASE_8

This stub implements the BaselineInterface but always abstains with a
DEFERRED_TO_PHASE_8 explanation.

The real Sage+Chaos implementation requires:
1. Online Boutique deployed on Linux (PENDING_LINUX)
2. Pre-labeled fault traces (not yet collected)
3. Sage evaluation harness (not yet integrated)

Do NOT fabricate Sage+Chaos results.
Do NOT remove this stub without first implementing the real baseline.

Authority: docs/baselines/SAGE_CHAOS.md, Phase 3.6 §11.
"""
from __future__ import annotations

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext


class SageChaosStub(BaselineInterface):
    """
    Sage+Chaos baseline stub.

    Status: DEFERRED_TO_PHASE_8

    Always abstains. Must be replaced with real implementation in Phase 8
    when pre-labeled trace data is available.
    """

    @property
    def baseline_id(self) -> str:
        return "B4-SAGE-CHAOS"

    def run(self, context: IncidentContext) -> BaselineOutput:
        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=[],
            abstained=True,
            notes=(
                "SAGE+CHAOS: DEFERRED_TO_PHASE_8. "
                "Pre-labeled fault trace data is not yet available. "
                "This stub must be replaced with a real implementation in Phase 8. "
                "Do NOT include these results in any paper table or comparison. "
                "See docs/baselines/SAGE_CHAOS.md."
            ),
        )
