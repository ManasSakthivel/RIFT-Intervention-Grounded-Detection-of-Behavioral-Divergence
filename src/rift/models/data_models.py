"""RIFT Phase 3A — Canonical data models.

All models use pydantic v2 BaseModel with field validators.
Immutable fields are documented; no in-place mutation should occur after construction.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Namespace pattern for intervention targets
# ---------------------------------------------------------------------------
_INTERVENTION_NAMESPACE_PREFIX = "rift-eval-"

_VALID_METRIC_NAMES = frozenset(
    {"lat_p99", "lat_p50", "err_rate", "rps", "cpu_pct", "mem_pct"}
)


# ===========================================================================
# Core system types
# ===========================================================================


class Service(BaseModel):
    """A microservice participating in the RIFT evaluation testbed."""

    service_id: str
    name: str
    namespace: str  # must match rift-eval-* for intervention targets
    replicas: int = 1
    instrumented: bool = True

    @field_validator("service_id")
    @classmethod
    def service_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("service_id must not be empty or whitespace")
        return v

    @field_validator("name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty or whitespace")
        return v

    @field_validator("replicas")
    @classmethod
    def replicas_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("replicas must be ≥ 1")
        return v


class Metric(BaseModel):
    """A single scalar metric observation for one service at one timestamp."""

    service_id: str
    metric_name: str  # lat_p99 | lat_p50 | err_rate | rps | cpu_pct | mem_pct
    value: float
    timestamp: float  # unix seconds
    collection_lag_s: float = 0.0  # actual collection lag observed
    aligned_window: Optional[int] = None  # window_id assigned after alignment

    @field_validator("metric_name")
    @classmethod
    def metric_name_valid(cls, v: str) -> str:
        if v not in _VALID_METRIC_NAMES:
            raise ValueError(
                f"metric_name must be one of {sorted(_VALID_METRIC_NAMES)}, got {v!r}"
            )
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("timestamp must be a positive unix epoch value")
        return v

    @field_validator("collection_lag_s")
    @classmethod
    def lag_non_negative(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("collection_lag_s must be ≥ 0.0")
        return v


class TimeWindow(BaseModel):
    """A discrete time window used for metric alignment and causal graph slicing."""

    window_id: int
    t_start: float
    t_end: float
    delta_t: float
    observations: List[Metric] = []

    @field_validator("window_id")
    @classmethod
    def window_id_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("window_id must be ≥ 0")
        return v

    @field_validator("delta_t")
    @classmethod
    def delta_t_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("delta_t must be > 0.0")
        return v

    @model_validator(mode="after")
    def window_bounds_consistent(self) -> "TimeWindow":
        if self.t_end <= self.t_start:
            raise ValueError("t_end must be strictly greater than t_start")
        return self


class CausalVariable(BaseModel):
    """A node in the time-sliced causal graph G_T."""

    var_id: str  # e.g., "frontend.lat_p99.t3"
    service_id: str
    metric_name: str
    time_index: int
    is_observable: bool = True
    is_endogenous: bool = True

    @field_validator("var_id")
    @classmethod
    def var_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("var_id must not be empty")
        return v

    @field_validator("time_index")
    @classmethod
    def time_index_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("time_index must be ≥ 0")
        return v


# ===========================================================================
# PAG (Partial Ancestral Graph) types
# ===========================================================================


class PAGEdgeType(str, Enum):
    DIRECTED = "DIRECTED"
    BIDIRECTED = "BIDIRECTED"
    PARTIALLY_DIRECTED = "PARTIALLY_DIRECTED"
    UNDIRECTED = "UNDIRECTED"


class PAGEdge(BaseModel):
    """A single edge in a Partial Ancestral Graph produced by FCI."""

    source: str
    target: str
    edge_type: PAGEdgeType
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("source", "target")
    @classmethod
    def endpoint_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("edge endpoint (source/target) must not be empty")
        return v

    @model_validator(mode="after")
    def source_target_differ(self) -> "PAGEdge":
        if self.source == self.target:
            raise ValueError("source and target must differ (no self-loops)")
        return self


# ===========================================================================
# Intervention types and status enums
# ===========================================================================


class InterventionType(str, Enum):
    LATENCY = "LATENCY"
    PACKET_LOSS = "PACKET_LOSS"
    BANDWIDTH_LIMIT = "BANDWIDTH_LIMIT"
    ERROR_RATE = "ERROR_RATE"


class ValidityStatus(str, Enum):
    VALID = "VALID"
    CONFOUNDED = "CONFOUNDED"
    INVALID = "INVALID"
    PENDING = "PENDING"


class RollbackStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class AuthorizationLevel(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    SUPERVISED = "SUPERVISED"
    DENIED = "DENIED"


class InterventionRecord(BaseModel):
    """Full audit record for one runtime intervention (do-operation)."""

    record_id: str  # UUID
    target_service: str
    target_variable: str
    target_destination: Optional[str] = None  # per-destination tc netem target
    nominal_value: float
    intervention_value: float
    intervention_type: InterventionType
    t_start: float
    t_end: Optional[float] = None
    pre_state_snapshot: Dict[str, float]
    post_state_snapshot: Dict[str, float]
    precision_achieved: Optional[float] = None
    precision_check_pass: Optional[bool] = None
    clean_window_pass: Optional[bool] = None
    concurrent_event_pass: Optional[bool] = None
    recovery_pass: Optional[bool] = None
    isolation_pass: Optional[bool] = None
    validity_status: ValidityStatus = ValidityStatus.PENDING
    rollback_status: RollbackStatus = RollbackStatus.NOT_ATTEMPTED
    safety_authorization: AuthorizationLevel
    affected_destinations: List[str] = []
    n_samples_collected: int = 0
    cid_result_ref: Optional[str] = None
    notes: str = ""

    @field_validator("record_id")
    @classmethod
    def record_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("record_id must not be empty")
        return v

    @field_validator("t_start")
    @classmethod
    def t_start_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("t_start must be a positive unix epoch value")
        return v

    @field_validator("n_samples_collected")
    @classmethod
    def n_samples_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("n_samples_collected must be ≥ 0")
        return v

    @model_validator(mode="after")
    def t_end_after_t_start(self) -> "InterventionRecord":
        if self.t_end is not None and self.t_end <= self.t_start:
            raise ValueError("t_end must be strictly greater than t_start when set")
        return self


# ===========================================================================
# CID (Causal Interventional Divergence) types
# ===========================================================================


class CIDGrade(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"  # n < 20
    CANDIDATE = "CANDIDATE"       # 20 ≤ n < 50
    RELIABLE = "RELIABLE"         # n ≥ 50


class CIDResult(BaseModel):
    """Result of one CID computation for a source→target variable pair."""

    result_id: str
    source_variable: str
    target_variable: str
    t_intervention: float
    w1_estimate: Optional[float] = None
    w1_ci_lower: Optional[float] = None
    w1_ci_upper: Optional[float] = None
    tv_diagnostic: Optional[float] = None
    permutation_pvalue: Optional[float] = None
    permutation_b: int = 10000
    permutation_significant: Optional[bool] = None
    alpha: float = 0.05
    n_baseline: int = 0
    n_post: int = 0
    grade: CIDGrade = CIDGrade.INSUFFICIENT
    theta_cid: float = 0.0
    exceeds_threshold: Optional[bool] = None
    intervention_record_id: Optional[str] = None
    notes: str = ""

    @field_validator("result_id")
    @classmethod
    def result_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("result_id must not be empty")
        return v

    @field_validator("alpha")
    @classmethod
    def alpha_in_range(cls, v: float) -> float:
        if not (0.0 < v < 1.0):
            raise ValueError("alpha must be in (0.0, 1.0)")
        return v

    @field_validator("permutation_b")
    @classmethod
    def permutation_b_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("permutation_b must be ≥ 1")
        return v

    @field_validator("n_baseline", "n_post")
    @classmethod
    def sample_counts_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("sample count must be ≥ 0")
        return v

    @field_validator("permutation_pvalue")
    @classmethod
    def pvalue_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("permutation_pvalue must be in [0.0, 1.0]")
        return v

    @field_validator("tv_diagnostic")
    @classmethod
    def tv_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("tv_diagnostic must be in [0.0, 1.0]")
        return v

    @model_validator(mode="after")
    def grade_consistent_with_samples(self) -> "CIDResult":
        """Grade must be consistent with n_baseline + n_post total."""
        n_total = self.n_baseline + self.n_post
        if self.grade == CIDGrade.RELIABLE and n_total < 50:
            raise ValueError(
                f"grade RELIABLE requires n_total ≥ 50; got {n_total}"
            )
        if self.grade == CIDGrade.CANDIDATE and not (20 <= n_total < 50):
            raise ValueError(
                f"grade CANDIDATE requires 20 ≤ n_total < 50; got {n_total}"
            )
        if self.grade == CIDGrade.INSUFFICIENT and n_total >= 20:
            raise ValueError(
                f"grade INSUFFICIENT requires n_total < 20; got {n_total}"
            )
        return self


# ===========================================================================
# EBD (Earliest Behavioral Divergence) types
# ===========================================================================


class EBDConfidence(str, Enum):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    DEFINITIVE = "DEFINITIVE"


class IdentifiabilityStatus(str, Enum):
    IDENTIFIABLE = "IDENTIFIABLE"
    CONDITIONALLY_IDENTIFIABLE = "CONDITIONALLY_IDENTIFIABLE"
    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"
    REQUIRES_INTERVENTION = "REQUIRES_INTERVENTION"


class EBDResult(BaseModel):
    """Result of an EBD determination for one variable at one incident time."""

    result_id: str
    service_id: str
    variable_id: str
    t_star: float  # timestamp of first divergence
    confidence: EBDConfidence
    r1_pass: bool = False  # Observed behavioral deviation
    r2_pass: bool = False  # Temporal precedence
    r3_pass: bool = False  # Causal relevance
    r4_pass: bool = False  # Intervention evidence
    cid_scores: Dict[str, Any] = {}
    boundary_limited: bool = False
    assumption_warnings: List[str] = []
    identifiability_state: IdentifiabilityStatus = IdentifiabilityStatus.IDENTIFIABLE
    intervention_record_ref: Optional[str] = None
    causal_path: List[Tuple[str, str]] = []
    notes: str = ""

    @field_validator("result_id", "service_id", "variable_id")
    @classmethod
    def str_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("string field must not be empty")
        return v

    @field_validator("t_star")
    @classmethod
    def t_star_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("t_star must be a positive unix epoch value")
        return v

    @model_validator(mode="after")
    def confidence_consistent_with_requirements(self) -> "EBDResult":
        """DEFINITIVE requires all four requirements; CANDIDATE requires R1-R3."""
        if self.confidence == EBDConfidence.DEFINITIVE:
            if not (self.r1_pass and self.r2_pass and self.r3_pass and self.r4_pass):
                raise ValueError(
                    "confidence DEFINITIVE requires r1_pass, r2_pass, r3_pass, r4_pass all True"
                )
        if self.confidence == EBDConfidence.CANDIDATE:
            if not (self.r1_pass and self.r2_pass and self.r3_pass):
                raise ValueError(
                    "confidence CANDIDATE requires r1_pass, r2_pass, r3_pass all True"
                )
        return self


# ===========================================================================
# Attribution and run types
# ===========================================================================


class Attribution(BaseModel):
    """Final causal attribution output for one incident."""

    attribution_id: str
    incident_id: str
    attributed_service: Optional[str] = None
    attributed_variable: Optional[str] = None
    confidence: EBDConfidence
    ebd_result_ref: str
    method: str  # "RIFT-FULL" | "RIFT-OBS" | baseline name
    is_abstaining: bool = False
    abstain_reason: Optional[str] = None  # NOT_IDENTIFIABLE | INSUFFICIENT_SAMPLES | etc.
    notes: str = ""

    @field_validator("attribution_id", "incident_id", "ebd_result_ref", "method")
    @classmethod
    def required_str_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("required string field must not be empty")
        return v

    @model_validator(mode="after")
    def abstain_reason_required_when_abstaining(self) -> "Attribution":
        if self.is_abstaining and not self.abstain_reason:
            raise ValueError(
                "abstain_reason must be provided when is_abstaining is True"
            )
        return self


class RIFTRun(BaseModel):
    """Top-level record for one complete RIFT attribution run."""

    run_id: str
    incident_id: str
    started_at: float
    completed_at: Optional[float] = None
    state_sequence: List[str]  # sequence of RIFTState values
    attribution: Optional[Attribution] = None
    intervention_records: List[str] = []  # InterventionRecord IDs
    total_ed_s: float = 0.0          # total elapsed detection seconds
    budget_remaining_s: float = 600.0
    stop_reason: Optional[str] = None
    notes: str = ""

    @field_validator("run_id", "incident_id")
    @classmethod
    def id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ID field must not be empty")
        return v

    @field_validator("started_at")
    @classmethod
    def started_at_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("started_at must be a positive unix epoch value")
        return v

    @field_validator("total_ed_s")
    @classmethod
    def total_ed_non_negative(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("total_ed_s must be ≥ 0.0")
        return v

    @field_validator("budget_remaining_s")
    @classmethod
    def budget_non_negative(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("budget_remaining_s must be ≥ 0.0")
        return v

    @model_validator(mode="after")
    def completed_at_after_started(self) -> "RIFTRun":
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must be ≥ started_at when set")
        return self
