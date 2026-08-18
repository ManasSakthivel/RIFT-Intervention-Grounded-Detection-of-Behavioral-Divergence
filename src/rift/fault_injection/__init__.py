"""RIFT Fault Injection module — Phase 3.5D.

Provides FaultInjector and FaultInjectionRecord for controlled, verified
fault injection against the RIFT fault benchmark (datasets/rift_faults/).

Scientific constraints:
- dry_run=True by default; never execute against production systems.
- verify_injection() is NOT optional: command success does not imply
  that the fault was measurably applied. All injection records must
  carry an explicit injection_verified flag set by an independent
  measurement.
- The manifest split (DEVELOPMENT=36, VALIDATION=18, HELD_OUT_TEST=15,
  seed=42) is immutable and checked at import time.

Authority: docs/PHASE_3_SPEC_FREEZE.md §11 / RIFT GATE 3.5D
"""

from src.rift.fault_injection.fault_injector import (
    FaultInjectionRecord,
    FaultInjectionStatus,
    FaultInjector,
    FaultScenario,
    FaultType,
)

__all__ = [
    "FaultInjector",
    "FaultInjectionRecord",
    "FaultInjectionStatus",
    "FaultScenario",
    "FaultType",
]
