"""RIFT Phase 3A gate tests — data model validation.

Tests every model for:
  1. Valid construction succeeds
  2. Invalid construction raises ValidationError (≥3 cases per model)
  3. JSON serialisation round-trip (model_dump_json → model_validate_json)
  4. model_dump() is deterministic (two calls produce equal dicts)
  5. Enum values are constrained (bad strings rejected)
  6. Optional fields default correctly

Gate 3A passes when this module exits with zero failures.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.rift.models.data_models import (
    Attribution,
    AuthorizationLevel,
    CIDGrade,
    CIDResult,
    CausalVariable,
    EBDConfidence,
    EBDResult,
    IdentifiabilityStatus,
    InterventionRecord,
    InterventionType,
    Metric,
    PAGEdge,
    PAGEdgeType,
    RIFTRun,
    RollbackStatus,
    Service,
    TimeWindow,
    ValidityStatus,
)


# ===========================================================================
# Helpers
# ===========================================================================


def round_trip(model_instance):
    """Serialise to JSON and deserialise; return the new instance."""
    cls = type(model_instance)
    return cls.model_validate_json(model_instance.model_dump_json())


def assert_round_trip_equal(model_instance):
    """Assert the round-tripped instance equals the original."""
    rt = round_trip(model_instance)
    assert rt == model_instance, f"Round-trip mismatch:\n  original: {model_instance}\n  result:   {rt}"


def assert_deterministic_dump(model_instance):
    """Assert two successive model_dump() calls return identical dicts."""
    d1 = model_instance.model_dump()
    d2 = model_instance.model_dump()
    assert d1 == d2, "model_dump() is not deterministic"


# ===========================================================================
# Service
# ===========================================================================


class TestService:
    def _valid(self, **overrides):
        defaults = dict(
            service_id="svc-frontend",
            name="frontend",
            namespace="rift-eval-default",
        )
        return Service(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_defaults(self):
        svc = self._valid()
        assert svc.replicas == 1
        assert svc.instrumented is True

    def test_valid_explicit(self):
        svc = self._valid(replicas=3, instrumented=False)
        assert svc.replicas == 3
        assert not svc.instrumented

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_service_id(self):
        with pytest.raises(ValidationError):
            self._valid(service_id="   ")

    def test_invalid_empty_name(self):
        with pytest.raises(ValidationError):
            self._valid(name="")

    def test_invalid_replicas_zero(self):
        with pytest.raises(ValidationError):
            self._valid(replicas=0)

    def test_invalid_replicas_negative(self):
        with pytest.raises(ValidationError):
            self._valid(replicas=-5)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# Metric
# ===========================================================================


class TestMetric:
    def _valid(self, **overrides):
        defaults = dict(
            service_id="svc-frontend",
            metric_name="lat_p99",
            value=42.5,
            timestamp=1_700_000_000.0,
        )
        return Metric(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_all_metric_names(self):
        for name in ("lat_p99", "lat_p50", "err_rate", "rps", "cpu_pct", "mem_pct"):
            m = self._valid(metric_name=name)
            assert m.metric_name == name

    def test_valid_optional_defaults(self):
        m = self._valid()
        assert m.collection_lag_s == 0.0
        assert m.aligned_window is None

    # -- invalid construction ------------------------------------------------

    def test_invalid_metric_name(self):
        with pytest.raises(ValidationError):
            self._valid(metric_name="p99_latency")

    def test_invalid_zero_timestamp(self):
        with pytest.raises(ValidationError):
            self._valid(timestamp=0.0)

    def test_invalid_negative_timestamp(self):
        with pytest.raises(ValidationError):
            self._valid(timestamp=-1.0)

    def test_invalid_negative_lag(self):
        with pytest.raises(ValidationError):
            self._valid(collection_lag_s=-0.1)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid(aligned_window=7))

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# TimeWindow
# ===========================================================================


class TestTimeWindow:
    def _valid(self, **overrides):
        defaults = dict(
            window_id=0,
            t_start=1_700_000_000.0,
            t_end=1_700_000_060.0,
            delta_t=60.0,
        )
        return TimeWindow(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_empty_observations(self):
        tw = self._valid()
        assert tw.observations == []

    def test_valid_window_id_zero(self):
        tw = self._valid(window_id=0)
        assert tw.window_id == 0

    # -- invalid construction ------------------------------------------------

    def test_invalid_negative_window_id(self):
        with pytest.raises(ValidationError):
            self._valid(window_id=-1)

    def test_invalid_zero_delta_t(self):
        with pytest.raises(ValidationError):
            self._valid(delta_t=0.0)

    def test_invalid_t_end_before_t_start(self):
        with pytest.raises(ValidationError):
            self._valid(t_start=1_700_000_060.0, t_end=1_700_000_000.0)

    def test_invalid_t_end_equal_t_start(self):
        with pytest.raises(ValidationError):
            self._valid(t_start=1_700_000_000.0, t_end=1_700_000_000.0)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# CausalVariable
# ===========================================================================


class TestCausalVariable:
    def _valid(self, **overrides):
        defaults = dict(
            var_id="frontend.lat_p99.t3",
            service_id="svc-frontend",
            metric_name="lat_p99",
            time_index=3,
        )
        return CausalVariable(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_defaults(self):
        cv = self._valid()
        assert cv.is_observable is True
        assert cv.is_endogenous is True

    def test_valid_exogenous(self):
        cv = self._valid(is_endogenous=False)
        assert not cv.is_endogenous

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_var_id(self):
        with pytest.raises(ValidationError):
            self._valid(var_id="")

    def test_invalid_whitespace_var_id(self):
        with pytest.raises(ValidationError):
            self._valid(var_id="   ")

    def test_invalid_negative_time_index(self):
        with pytest.raises(ValidationError):
            self._valid(time_index=-1)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# PAGEdge
# ===========================================================================


class TestPAGEdge:
    def _valid(self, **overrides):
        defaults = dict(
            source="frontend.lat_p99.t3",
            target="cartservice.lat_p99.t4",
            edge_type=PAGEdgeType.DIRECTED,
            confidence=0.85,
        )
        return PAGEdge(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_all_edge_types(self):
        for et in PAGEdgeType:
            e = self._valid(edge_type=et)
            assert e.edge_type == et

    def test_valid_confidence_boundaries(self):
        for c in (0.0, 1.0):
            e = self._valid(confidence=c)
            assert e.confidence == c

    # -- invalid construction ------------------------------------------------

    def test_invalid_bad_edge_type(self):
        with pytest.raises(ValidationError):
            self._valid(edge_type="CAUSAL")

    def test_invalid_self_loop(self):
        with pytest.raises(ValidationError):
            self._valid(source="node_A", target="node_A")

    def test_invalid_confidence_above_one(self):
        with pytest.raises(ValidationError):
            self._valid(confidence=1.01)

    def test_invalid_confidence_below_zero(self):
        with pytest.raises(ValidationError):
            self._valid(confidence=-0.01)

    def test_invalid_empty_source(self):
        with pytest.raises(ValidationError):
            self._valid(source="")

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())

    # -- enum constraint -----------------------------------------------------

    def test_enum_values_constrained(self):
        valid_values = {e.value for e in PAGEdgeType}
        assert "DIRECTED" in valid_values
        assert "CAUSALLY_ACCURATE" not in valid_values


# ===========================================================================
# InterventionRecord
# ===========================================================================


_IR_BASE = dict(
    record_id="a1b2c3d4-0000-0000-0000-000000000001",
    target_service="svc-cartservice",
    target_variable="lat_p99",
    nominal_value=50.0,
    intervention_value=300.0,
    intervention_type=InterventionType.LATENCY,
    t_start=1_700_000_100.0,
    pre_state_snapshot={"lat_p99": 48.5, "err_rate": 0.001},
    post_state_snapshot={"lat_p99": 298.0, "err_rate": 0.002},
    safety_authorization=AuthorizationLevel.AUTONOMOUS,
)


class TestInterventionRecord:
    def _valid(self, **overrides):
        return InterventionRecord(**(_IR_BASE | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_defaults(self):
        ir = self._valid()
        assert ir.validity_status == ValidityStatus.PENDING
        assert ir.rollback_status == RollbackStatus.NOT_ATTEMPTED
        assert ir.n_samples_collected == 0
        assert ir.affected_destinations == []
        assert ir.target_destination is None

    def test_valid_with_t_end(self):
        ir = self._valid(t_end=1_700_000_160.0)
        assert ir.t_end > ir.t_start

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_record_id(self):
        with pytest.raises(ValidationError):
            self._valid(record_id="")

    def test_invalid_zero_t_start(self):
        with pytest.raises(ValidationError):
            self._valid(t_start=0.0)

    def test_invalid_t_end_before_t_start(self):
        with pytest.raises(ValidationError):
            self._valid(t_end=1_699_999_999.0)

    def test_invalid_negative_n_samples(self):
        with pytest.raises(ValidationError):
            self._valid(n_samples_collected=-1)

    def test_invalid_bad_intervention_type(self):
        with pytest.raises(ValidationError):
            self._valid(intervention_type="CPU_THROTTLE")

    def test_invalid_bad_auth_level(self):
        with pytest.raises(ValidationError):
            self._valid(safety_authorization="ELEVATED")

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())

    # -- enum defaults -------------------------------------------------------

    def test_validity_status_default(self):
        ir = self._valid()
        assert ir.validity_status == ValidityStatus.PENDING

    def test_rollback_status_default(self):
        ir = self._valid()
        assert ir.rollback_status == RollbackStatus.NOT_ATTEMPTED


# ===========================================================================
# CIDResult
# ===========================================================================


class TestCIDResult:
    def _valid(self, **overrides):
        defaults = dict(
            result_id="cid-001",
            source_variable="frontend.lat_p99.t3",
            target_variable="cartservice.lat_p99.t4",
            t_intervention=1_700_000_100.0,
            n_baseline=0,
            n_post=0,
            grade=CIDGrade.INSUFFICIENT,
        )
        return CIDResult(**(defaults | overrides))

    def _reliable(self, **overrides):
        defaults = dict(
            result_id="cid-002",
            source_variable="frontend.lat_p99.t3",
            target_variable="cartservice.lat_p99.t4",
            t_intervention=1_700_000_100.0,
            n_baseline=30,
            n_post=25,
            grade=CIDGrade.RELIABLE,
        )
        return CIDResult(**(defaults | overrides))

    def _candidate(self, **overrides):
        defaults = dict(
            result_id="cid-003",
            source_variable="frontend.lat_p99.t3",
            target_variable="cartservice.lat_p99.t4",
            t_intervention=1_700_000_100.0,
            n_baseline=15,
            n_post=10,
            grade=CIDGrade.CANDIDATE,
        )
        return CIDResult(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_insufficient(self):
        cid = self._valid()
        assert cid.grade == CIDGrade.INSUFFICIENT

    def test_valid_reliable(self):
        cid = self._reliable()
        assert cid.grade == CIDGrade.RELIABLE

    def test_valid_candidate(self):
        cid = self._candidate()
        assert cid.grade == CIDGrade.CANDIDATE

    def test_valid_defaults(self):
        cid = self._valid()
        assert cid.permutation_b == 10000
        assert cid.alpha == 0.05
        assert cid.theta_cid == 0.0
        assert cid.w1_estimate is None

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_result_id(self):
        with pytest.raises(ValidationError):
            self._valid(result_id="")

    def test_invalid_alpha_zero(self):
        with pytest.raises(ValidationError):
            self._valid(alpha=0.0)

    def test_invalid_alpha_one(self):
        with pytest.raises(ValidationError):
            self._valid(alpha=1.0)

    def test_invalid_pvalue_negative(self):
        with pytest.raises(ValidationError):
            self._valid(permutation_pvalue=-0.01)

    def test_invalid_pvalue_above_one(self):
        with pytest.raises(ValidationError):
            self._valid(permutation_pvalue=1.01)

    def test_invalid_tv_above_one(self):
        with pytest.raises(ValidationError):
            self._valid(tv_diagnostic=1.5)

    def test_invalid_permutation_b_zero(self):
        with pytest.raises(ValidationError):
            self._valid(permutation_b=0)

    def test_invalid_grade_reliable_insufficient_samples(self):
        with pytest.raises(ValidationError):
            self._valid(n_baseline=10, n_post=5, grade=CIDGrade.RELIABLE)

    def test_invalid_grade_candidate_wrong_samples(self):
        # n_total = 5, which is < 20, so CANDIDATE is invalid
        with pytest.raises(ValidationError):
            self._valid(n_baseline=3, n_post=2, grade=CIDGrade.CANDIDATE)

    def test_invalid_grade_insufficient_too_many_samples(self):
        with pytest.raises(ValidationError):
            self._valid(n_baseline=10, n_post=15, grade=CIDGrade.INSUFFICIENT)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_round_trip_reliable(self):
        assert_round_trip_equal(self._reliable())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# EBDResult
# ===========================================================================


class TestEBDResult:
    def _valid_none(self, **overrides):
        defaults = dict(
            result_id="ebd-001",
            service_id="svc-frontend",
            variable_id="frontend.lat_p99.t3",
            t_star=1_700_000_100.0,
            confidence=EBDConfidence.NONE,
        )
        return EBDResult(**(defaults | overrides))

    def _valid_candidate(self, **overrides):
        defaults = dict(
            result_id="ebd-002",
            service_id="svc-frontend",
            variable_id="frontend.lat_p99.t3",
            t_star=1_700_000_100.0,
            confidence=EBDConfidence.CANDIDATE,
            r1_pass=True,
            r2_pass=True,
            r3_pass=True,
        )
        return EBDResult(**(defaults | overrides))

    def _valid_definitive(self, **overrides):
        defaults = dict(
            result_id="ebd-003",
            service_id="svc-frontend",
            variable_id="frontend.lat_p99.t3",
            t_star=1_700_000_100.0,
            confidence=EBDConfidence.DEFINITIVE,
            r1_pass=True,
            r2_pass=True,
            r3_pass=True,
            r4_pass=True,
        )
        return EBDResult(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_none_confidence(self):
        ebd = self._valid_none()
        assert ebd.confidence == EBDConfidence.NONE
        assert ebd.boundary_limited is False
        assert ebd.causal_path == []

    def test_valid_candidate(self):
        ebd = self._valid_candidate()
        assert ebd.confidence == EBDConfidence.CANDIDATE

    def test_valid_definitive(self):
        ebd = self._valid_definitive()
        assert ebd.confidence == EBDConfidence.DEFINITIVE

    def test_valid_causal_path(self):
        ebd = self._valid_definitive(
            causal_path=[("frontend.lat_p99.t3", "cart.lat_p99.t4")]
        )
        assert len(ebd.causal_path) == 1

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_result_id(self):
        with pytest.raises(ValidationError):
            self._valid_none(result_id="")

    def test_invalid_zero_t_star(self):
        with pytest.raises(ValidationError):
            self._valid_none(t_star=0.0)

    def test_invalid_definitive_missing_r4(self):
        with pytest.raises(ValidationError):
            self._valid_definitive(r4_pass=False)

    def test_invalid_definitive_missing_r1(self):
        with pytest.raises(ValidationError):
            self._valid_definitive(r1_pass=False)

    def test_invalid_candidate_missing_r3(self):
        with pytest.raises(ValidationError):
            self._valid_candidate(r3_pass=False)

    def test_invalid_empty_variable_id(self):
        with pytest.raises(ValidationError):
            self._valid_none(variable_id="  ")

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip_none(self):
        assert_round_trip_equal(self._valid_none())

    def test_round_trip_definitive(self):
        assert_round_trip_equal(self._valid_definitive())

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid_definitive())

    # -- identifiability default ---------------------------------------------

    def test_identifiability_default(self):
        ebd = self._valid_none()
        assert ebd.identifiability_state == IdentifiabilityStatus.IDENTIFIABLE


# ===========================================================================
# Attribution
# ===========================================================================


class TestAttribution:
    def _valid(self, **overrides):
        defaults = dict(
            attribution_id="attr-001",
            incident_id="inc-2024-001",
            attributed_service="svc-cartservice",
            attributed_variable="lat_p99",
            confidence=EBDConfidence.DEFINITIVE,
            ebd_result_ref="ebd-003",
            method="RIFT-FULL",
        )
        return Attribution(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_with_attribution(self):
        attr = self._valid()
        assert attr.is_abstaining is False
        assert attr.abstain_reason is None

    def test_valid_abstaining(self):
        attr = self._valid(
            attributed_service=None,
            attributed_variable=None,
            confidence=EBDConfidence.NONE,
            is_abstaining=True,
            abstain_reason="NOT_IDENTIFIABLE",
        )
        assert attr.is_abstaining is True
        assert attr.abstain_reason == "NOT_IDENTIFIABLE"

    def test_valid_optional_service_variable(self):
        attr = self._valid(
            attributed_service=None,
            attributed_variable=None,
            is_abstaining=True,
            abstain_reason="INSUFFICIENT_SAMPLES",
        )
        assert attr.attributed_service is None

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_attribution_id(self):
        with pytest.raises(ValidationError):
            self._valid(attribution_id="")

    def test_invalid_empty_incident_id(self):
        with pytest.raises(ValidationError):
            self._valid(incident_id="  ")

    def test_invalid_empty_method(self):
        with pytest.raises(ValidationError):
            self._valid(method="")

    def test_invalid_abstaining_no_reason(self):
        with pytest.raises(ValidationError):
            self._valid(is_abstaining=True, abstain_reason=None)

    def test_invalid_bad_confidence_enum(self):
        with pytest.raises(ValidationError):
            self._valid(confidence="HIGH")

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_round_trip_abstaining(self):
        attr = self._valid(
            is_abstaining=True,
            abstain_reason="NOT_IDENTIFIABLE",
            confidence=EBDConfidence.NONE,
            attributed_service=None,
            attributed_variable=None,
        )
        assert_round_trip_equal(attr)

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# RIFTRun
# ===========================================================================


class TestRIFTRun:
    def _valid(self, **overrides):
        defaults = dict(
            run_id="run-001",
            incident_id="inc-2024-001",
            started_at=1_700_000_000.0,
            state_sequence=["INIT", "OBSERVING", "PLANNING", "DONE"],
        )
        return RIFTRun(**(defaults | overrides))

    # -- valid construction --------------------------------------------------

    def test_valid_defaults(self):
        run = self._valid()
        assert run.total_ed_s == 0.0
        assert run.budget_remaining_s == 600.0
        assert run.completed_at is None
        assert run.attribution is None
        assert run.intervention_records == []
        assert run.stop_reason is None

    def test_valid_with_completed_at(self):
        run = self._valid(completed_at=1_700_000_300.0)
        assert run.completed_at > run.started_at

    def test_valid_empty_state_sequence(self):
        run = self._valid(state_sequence=[])
        assert run.state_sequence == []

    # -- invalid construction ------------------------------------------------

    def test_invalid_empty_run_id(self):
        with pytest.raises(ValidationError):
            self._valid(run_id="")

    def test_invalid_zero_started_at(self):
        with pytest.raises(ValidationError):
            self._valid(started_at=0.0)

    def test_invalid_completed_before_started(self):
        with pytest.raises(ValidationError):
            self._valid(
                started_at=1_700_000_100.0,
                completed_at=1_700_000_000.0,
            )

    def test_invalid_negative_total_ed(self):
        with pytest.raises(ValidationError):
            self._valid(total_ed_s=-1.0)

    def test_invalid_negative_budget(self):
        with pytest.raises(ValidationError):
            self._valid(budget_remaining_s=-10.0)

    # -- round-trip & determinism --------------------------------------------

    def test_round_trip(self):
        assert_round_trip_equal(self._valid())

    def test_round_trip_with_attribution(self):
        attr = Attribution(
            attribution_id="attr-001",
            incident_id="inc-2024-001",
            attributed_service="svc-cartservice",
            attributed_variable="lat_p99",
            confidence=EBDConfidence.DEFINITIVE,
            ebd_result_ref="ebd-003",
            method="RIFT-FULL",
        )
        run = self._valid(attribution=attr, completed_at=1_700_000_600.0)
        assert_round_trip_equal(run)

    def test_deterministic_dump(self):
        assert_deterministic_dump(self._valid())


# ===========================================================================
# Cross-cutting: enum constraints
# ===========================================================================


class TestEnumConstraints:
    """Verify that all enum fields reject unknown string values."""

    def test_pag_edge_type_rejects_unknown(self):
        with pytest.raises(ValidationError):
            PAGEdge(
                source="A",
                target="B",
                edge_type="CAUSAL",
                confidence=0.5,
            )

    def test_intervention_type_rejects_unknown(self):
        with pytest.raises(ValidationError):
            base = {k: v for k, v in _IR_BASE.items() if k != "intervention_type"}
            InterventionRecord(
                **base,  # type: ignore[arg-type]
                intervention_type="CPU_THROTTLE",
            )

    def test_validity_status_rejects_unknown(self):
        with pytest.raises(ValidationError):
            InterventionRecord(
                **{**_IR_BASE, "validity_status": "PARTIAL"},  # type: ignore[arg-type]
            )

    def test_rollback_status_rejects_unknown(self):
        with pytest.raises(ValidationError):
            InterventionRecord(
                **{**_IR_BASE, "rollback_status": "MAYBE"},  # type: ignore[arg-type]
            )

    def test_auth_level_rejects_unknown(self):
        with pytest.raises(ValidationError):
            InterventionRecord(
                **{**_IR_BASE, "safety_authorization": "ELEVATED"},  # type: ignore[arg-type]
            )

    def test_cid_grade_rejects_unknown(self):
        with pytest.raises(ValidationError):
            CIDResult(
                result_id="x",
                source_variable="A",
                target_variable="B",
                t_intervention=1_700_000_000.0,
                grade="GOOD",
            )

    def test_ebd_confidence_rejects_unknown(self):
        with pytest.raises(ValidationError):
            EBDResult(
                result_id="x",
                service_id="svc",
                variable_id="var",
                t_star=1_700_000_000.0,
                confidence="HIGH",
            )

    def test_identifiability_status_rejects_unknown(self):
        with pytest.raises(ValidationError):
            EBDResult(
                result_id="x",
                service_id="svc",
                variable_id="var",
                t_star=1_700_000_000.0,
                confidence=EBDConfidence.NONE,
                identifiability_state="MAYBE",
            )


# ===========================================================================
# Cross-cutting: JSON serialisation uses value strings (not enum objects)
# ===========================================================================


class TestJSONSerialisationContent:
    """Verify the serialised JSON contains string values, not Python enum reprs."""

    def test_intervention_type_serialised_as_string(self):
        ir = InterventionRecord(**_IR_BASE)
        data = json.loads(ir.model_dump_json())
        assert data["intervention_type"] == "LATENCY"

    def test_validity_status_serialised_as_string(self):
        ir = InterventionRecord(**_IR_BASE)
        data = json.loads(ir.model_dump_json())
        assert data["validity_status"] == "PENDING"

    def test_cid_grade_serialised_as_string(self):
        cid = CIDResult(
            result_id="x",
            source_variable="A",
            target_variable="B",
            t_intervention=1_700_000_000.0,
            grade=CIDGrade.INSUFFICIENT,
        )
        data = json.loads(cid.model_dump_json())
        assert data["grade"] == "INSUFFICIENT"

    def test_ebd_confidence_serialised_as_string(self):
        ebd = EBDResult(
            result_id="x",
            service_id="svc",
            variable_id="var",
            t_star=1_700_000_000.0,
            confidence=EBDConfidence.NONE,
        )
        data = json.loads(ebd.model_dump_json())
        assert data["confidence"] == "NONE"

    def test_pag_edge_type_serialised_as_string(self):
        edge = PAGEdge(
            source="A", target="B", edge_type=PAGEdgeType.BIDIRECTED, confidence=0.7
        )
        data = json.loads(edge.model_dump_json())
        assert data["edge_type"] == "BIDIRECTED"
