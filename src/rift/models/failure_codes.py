"""RIFT Failure / Abstention Taxonomy — Phase 3.6 §29.

Every unsuccessful RIFT run must produce one or more explicit FailureCode values.
No run may return a generic "FAILED" status without an accompanying code.

Authority: Phase 3.6 specification §29.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class FailureCode(str, Enum):
    """
    Taxonomy of RIFT failure and abstention reasons.

    NOT_IDENTIFIABLE:
        The query P(Y | do(X)) cannot be estimated from the PAG.
        The identifiability algorithm returned ABSTAIN.
        RIFT must not attempt attribution.

    INSUFFICIENT_SAMPLES:
        n_min < 20 (SPEC-AMEND-003, CIDGrade.INSUFFICIENT).
        CID cannot be computed. Attribution ABSTAINED.

    GRAPH_DISCOVERY_FAILURE:
        FCI failed to produce a valid PAG (e.g., too few samples, numerical
        issues, or subgraph k=0). No causal structure available.

    INTERVENTION_FAILURE:
        tc/netem apply command returned non-zero or verification failed.
        The intervention was not confirmed active.

    INTERVENTION_NOT_VERIFIED:
        Intervention command succeeded (returncode=0) but independent
        measurement (ping, tc -s) did not confirm the fault is active.
        Distinct from INTERVENTION_FAILURE.

    BOUNDARY_LIMITED:
        The anomaly subgraph hit the k≤15 boundary constraint.
        Attribution may be incomplete (some services excluded).

    SAFETY_ABORT:
        One of the 8 hard safety stops triggered.
        The pipeline halted before completing attribution.

    TELEMETRY_FAILURE:
        The Prometheus / OTEL telemetry pipeline did not deliver usable data.
        Includes: scrape failure, empty response, network error.

    TIME_ALIGNMENT_FAILURE:
        Metric timestamps could not be aligned to the Δt=10s window grid.
        Causally-consistent time-slice construction aborted.

    BUDGET_EXHAUSTED:
        Cumulative execution duration exceeded T_budget (600s default).
        Pipeline stopped before entropy convergence.

    ALL_CANDIDATES_NON_IDENTIFIABLE:
        All candidate services are in NOT_IDENTIFIABLE state.
        No attribution possible; RIFT abstains entirely.

    UNKNOWN:
        An unexpected error occurred. Should never be used if the above codes
        apply. Indicates a programming error that must be investigated.
    """

    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    GRAPH_DISCOVERY_FAILURE = "GRAPH_DISCOVERY_FAILURE"
    INTERVENTION_FAILURE = "INTERVENTION_FAILURE"
    INTERVENTION_NOT_VERIFIED = "INTERVENTION_NOT_VERIFIED"
    BOUNDARY_LIMITED = "BOUNDARY_LIMITED"
    SAFETY_ABORT = "SAFETY_ABORT"
    TELEMETRY_FAILURE = "TELEMETRY_FAILURE"
    TIME_ALIGNMENT_FAILURE = "TIME_ALIGNMENT_FAILURE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ALL_CANDIDATES_NON_IDENTIFIABLE = "ALL_CANDIDATES_NON_IDENTIFIABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class FailureRecord:
    """
    Structured record of one or more failure codes for a RIFT run.

    A run may have multiple codes (e.g., BOUNDARY_LIMITED + INSUFFICIENT_SAMPLES
    if the subgraph was pruned AND sample counts were low).

    Attach this record to RIFTRunRecord.failure_record when final_state != PASS.
    """

    run_id: str
    codes: List[FailureCode] = field(default_factory=list)
    primary_code: Optional[FailureCode] = None  # most specific / impactful code
    details: str = ""  # human-readable context

    def add(self, code: FailureCode, detail: str = "") -> "FailureRecord":
        """Append a failure code. Returns self for chaining."""
        if code not in self.codes:
            self.codes.append(code)
        if self.primary_code is None:
            self.primary_code = code
        if detail:
            sep = "; " if self.details else ""
            self.details = self.details + sep + detail
        return self

    def is_abstention(self) -> bool:
        """True if the failure is a sanctioned RIFT abstention (not an error)."""
        abstention_codes = {
            FailureCode.NOT_IDENTIFIABLE,
            FailureCode.INSUFFICIENT_SAMPLES,
            FailureCode.ALL_CANDIDATES_NON_IDENTIFIABLE,
        }
        return bool(self.codes) and set(self.codes).issubset(
            abstention_codes | {FailureCode.BOUNDARY_LIMITED}
        )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "codes": [c.value for c in self.codes],
            "primary_code": self.primary_code.value if self.primary_code else None,
            "is_abstention": self.is_abstention(),
            "details": self.details,
        }
