"""
Sprint 4.2.3 — EBD validation and adversarial attribution regression tests.

Each test documents a behaviour that was demonstrated (or confirmed correct) during
the Sprint 4.2.3 audit. Tests tagged DEFECT failed against the pre-4.2.3 code.
Synthetic ground-truth scenarios only; no claim about real systems.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import pytest

from rift.ebd.ebd import _check_r1, _cid_supports_r4, compute_ebd
from rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult

STEP = 10.0
B = {"mean": 0.0, "std": 10.0}


def _pag(variables: List[str], edges: List[Tuple[str, str, str]]) -> PAGResult:
    return PAGResult(
        variables=variables,
        edges=[PAGEdge(s, t, PAGEdgeType(ty)) for s, t, ty in edges],
    )


def _series(onset: float, n: int = 12, amp: float = 50.0, drop: Tuple[float, ...] = (),
            noise: Optional[List[float]] = None) -> pd.DataFrame:
    ts = [i * STEP for i in range(n)]
    rows = []
    for i, t in enumerate(ts):
        if t in drop:
            continue
        v = amp if t >= onset else 0.0
        if noise:
            v += noise[i % len(noise)]
        rows.append((t, v))
    return pd.DataFrame(rows, columns=["time", "value"])


WINDOW = (0.0, 110.0)


def _by(results, svc):
    return next((r for r in results if r.service_id == svc), None)


# ─────────────────────────── EBD: earliest, not largest ───────────────────────────

class TestEarliestNotLargest:
    def test_earlier_small_beats_later_huge(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(30, amp=35.0), "B": _series(70, amp=500.0)}
        res = compute_ebd(m, {"A": B, "B": B}, pag, WINDOW)
        assert res[0].service_id == "A"
        assert res[0].t_star < _by(res, "B").t_star

    def test_multiple_services_different_onsets_ordering(self):
        pag = _pag(["A", "B", "C"], [("A", "B", "DIRECTED"), ("B", "C", "DIRECTED")])
        m = {"A": _series(20), "B": _series(40), "C": _series(60)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert [r.service_id for r in res] == ["A", "B", "C"]
        assert res[0].confidence == "CANDIDATE"
        assert _by(res, "B").confidence == "NONE" and not _by(res, "B").r2_pass

    def test_simultaneous_onset_is_a_documented_tie(self):
        """Same-window onset cannot be ordered by timing. The ancestor A is CANDIDATE;
        the leaf B is ALSO CANDIDATE via the deliberate P1-11 R3-leaf rule (upstream
        diverging same-time). This is a known, documented tie, not a precedence claim."""
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(30), "B": _series(30)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert _by(res, "A").confidence == "CANDIDATE"
        assert _by(res, "A").t_star == _by(res, "B").t_star

    def test_simultaneous_onset_reverse_edge_ancestor_still_candidate(self):
        pag = _pag(["A", "B"], [("B", "A", "DIRECTED")])
        m = {"A": _series(30), "B": _series(30)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert _by(res, "B").confidence == "CANDIDATE"

    def test_high_variance_service_not_flagged_by_noise(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        noisy = {"mean": 0.0, "std": 60.0}
        m = {"A": _series(40, amp=50.0), "B": _series(10, amp=60.0)}  # B's 60 = 1 sigma
        res = compute_ebd(m, {"A": B, "B": noisy}, pag, WINDOW)
        assert _by(res, "B") is None  # no R1 for B; A is sole divergent service
        assert res[0].service_id == "A"

    def test_abstain_when_no_persistent_evidence(self):
        pag = _pag(["A"], [])
        one_spike = pd.DataFrame({"time": [0, 10, 20, 30], "value": [0, 90, 0, 0]})
        assert compute_ebd({"A": one_spike}, {"A": B}, pag, (0, 30)) == []

    def test_abstain_when_baseline_std_zero(self):
        ok, t, _ = _check_r1(_series(30), 0.0, 0.0, 3.0, 2, STEP, 0.0)
        assert ok is False and t == float("inf")


# ─────────────── DEFECT: strict-earlier R2 failure must not be overridden ───────────────

class TestR2StrictPrecedence:
    def test_upstream_that_diverges_after_downstream_fails_r2(self):
        """DEFECT (pre-4.2.3): a graph ancestor A was promoted to CANDIDATE even though
        its descendant B diverged strictly earlier (tie-resolution block overrode R2)."""
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(60), "B": _series(10)}
        res = compute_ebd(m, {"A": B, "B": B}, pag, WINDOW)
        a, b = _by(res, "A"), _by(res, "B")
        assert a.r2_pass is False
        assert a.confidence == "NONE"
        assert res[0].service_id == "B"
        assert b.t_star < a.t_star

    def test_early_downstream_symptom_with_late_upstream_is_not_root_via_upstream(self):
        # three-node chain; middle node diverges first
        pag = _pag(["A", "B", "C"], [("A", "B", "DIRECTED"), ("B", "C", "DIRECTED")])
        m = {"A": _series(80), "B": _series(20), "C": _series(50)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert _by(res, "A").confidence == "NONE"
        assert res[0].service_id == "B"


# ─────────────────────── Missing telemetry / direction ───────────────────────

class TestMissingTelemetryAndDirection:
    def test_default_strict_gap_breaks_run_historical_behaviour(self):
        df = _series(30, drop=(40.0,))
        ok, t, _ = _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0)
        # windows 30, 50, 60,... -> 50,60 still form a run starting at 50
        assert ok is True and t == 50.0

    def test_max_gap_bridges_dropped_window_and_recovers_true_onset(self):
        df = _series(30, drop=(40.0,))
        ok, t, _ = _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0, max_gap_windows=1)
        assert ok is True and t == 30.0

    def test_observed_non_exceeding_window_always_breaks_run(self):
        df = pd.DataFrame({"time": [0, 10, 20, 30, 40], "value": [0, 50, 0, 50, 0]})
        ok, _, _ = _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0, max_gap_windows=3)
        assert ok is False

    def test_dropout_does_not_create_false_divergence(self):
        df = _series(1000, drop=(20.0, 50.0, 70.0))  # never diverges
        ok, _, _ = _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0, max_gap_windows=2)
        assert ok is False

    def test_negative_deviation_default_is_bidirectional(self):
        df = _series(30, amp=-50.0)
        assert _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0)[0] is True

    def test_direction_increase_ignores_drop(self):
        df = _series(30, amp=-50.0)
        assert _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0, direction="increase")[0] is False
        assert _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0, direction="decrease")[0] is True
        assert _check_r1(_series(30), 0.0, 10.0, 3.0, 2, STEP, 0.0, direction="increase")[0] is True

    def test_invalid_direction_rejected(self):
        with pytest.raises(ValueError):
            _check_r1(_series(30), 0.0, 10.0, 3.0, 2, STEP, 0.0, direction="up")

    def test_compute_ebd_missing_service_telemetry_is_not_fabricated(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        res = compute_ebd({"A": _series(30)}, {"A": B, "B": B}, pag, WINDOW)
        assert [r.service_id for r in res] == ["A"]

    def test_anomaly_score_is_from_divergence_run_not_whole_window(self):
        """DEFECT (pre-4.2.3): max |z| over the whole window was reported, so a pre-run
        isolated spike inflated the score of the run that actually triggered detection."""
        df = pd.DataFrame({
            "time": [0, 10, 20, 30, 40, 50],
            "value": [0, 200, 0, 50, 50, 50],  # isolated spike at t=10 (z=20), run from 30
        })
        ok, t, score = _check_r1(df, 0.0, 10.0, 3.0, 2, STEP, 0.0)
        assert ok and t == 30.0
        assert score == pytest.approx(5.0)


# ───────────────────────── Attribution: adversarial regressions ─────────────────────────

class TestSemiDirectedNotCausalAncestry:
    def test_oo_edge_does_not_give_both_ends_candidate(self):
        """DEFECT (pre-4.2.3): an o-o edge produced CANDIDATE for both the earlier and
        the later service. The later one now fails R2 (strictly later), and the earlier
        one is flagged as semi-directed (reachability only)."""
        pag = _pag(["A", "B"], [("A", "B", "UNDIRECTED")])
        m = {"A": _series(30), "B": _series(50)}
        res = compute_ebd(m, {"A": B, "B": B}, pag, WINDOW)
        assert _by(res, "B").confidence == "NONE"
        a = _by(res, "A")
        assert a.causal_path_kind == "SEMI_DIRECTED"
        assert any("semi-directed" in w for w in a.assumption_warnings)

    def test_directed_path_is_labelled_directed(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        res = compute_ebd({"A": _series(30), "B": _series(50)}, {"A": B, "B": B}, pag, WINDOW)
        a = _by(res, "A")
        assert a.causal_path_kind == "DIRECTED"
        assert not any("semi-directed" in w for w in a.assumption_warnings)

    def test_partially_directed_chain_marked_semi(self):
        pag = _pag(["A", "B"], [("A", "B", "PARTIALLY_DIRECTED")])
        res = compute_ebd({"A": _series(30), "B": _series(50)}, {"A": B, "B": B}, pag, WINDOW)
        assert _by(res, "A").causal_path_kind == "SEMI_DIRECTED"

    def test_bidirected_only_gives_no_causal_path(self):
        pag = _pag(["A", "B"], [("A", "B", "BIDIRECTED")])
        res = compute_ebd({"A": _series(30), "B": _series(50)}, {"A": B, "B": B}, pag, WINDOW)
        a = _by(res, "A")
        assert a.r3_pass is False and a.confidence == "NONE"
        assert a.identifiability_state == "NOT_IDENTIFIABLE"


class TestDownstreamSymptomsNotRoots:
    def test_downstream_leaf_symptom_not_root(self):
        pag = _pag(["A", "B", "C"], [("A", "B", "DIRECTED"), ("B", "C", "DIRECTED")])
        m = {"A": _series(20), "B": _series(30), "C": _series(40)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert _by(res, "C").confidence == "NONE"
        assert _by(res, "B").confidence == "NONE"
        assert res[0].service_id == "A"

    def test_larger_downstream_symptom_never_ranked_first(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(20, amp=40.0), "B": _series(30, amp=900.0)}
        res = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        assert res[0].service_id == "A"


class TestInterventionVsObservational:
    class _CID:
        def __init__(self, w1=1.5, grade="RELIABLE", perm=True, exceeds=True):
            self.w1_estimate = w1
            self.w1_ci_lower = 1.0
            self.w1_ci_upper = 2.0
            self.n_post = 50
            self.permutation_significant = perm
            self.exceeds_threshold = exceeds

            class _G:
                pass
            _G.value = grade
            self.grade = _G

    def _run(self, cid):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(30), "B": _series(50)}
        return _by(compute_ebd(m, {"A": B, "B": B}, pag, WINDOW,
                               cid_results={"A→B": cid} if cid else None), "A")

    def test_no_cid_means_observational_candidate(self):
        a = self._run(None)
        assert a.confidence == "CANDIDATE" and a.evidence_type == "OBSERVATIONAL"

    def test_valid_cid_upgrades_to_definitive_interventional(self):
        a = self._run(self._CID())
        assert a.confidence == "DEFINITIVE" and a.evidence_type == "INTERVENTIONAL"

    def test_insufficient_grade_cid_does_not_upgrade(self):
        """DEFECT (pre-4.2.3): grade was ignored when deciding R4."""
        a = self._run(self._CID(grade="INSUFFICIENT"))
        assert a.r4_pass is False and a.confidence == "CANDIDATE"

    def test_non_significant_permutation_does_not_upgrade(self):
        a = self._run(self._CID(perm=False))
        assert a.r4_pass is False and a.confidence == "CANDIDATE"

    def test_below_iqr_threshold_does_not_upgrade(self):
        a = self._run(self._CID(exceeds=False))
        assert a.r4_pass is False

    def test_mock_without_required_fields_is_rejected(self):
        """Sprint 4.2.4 tightening: evidence lacking permutation/threshold fields is not accepted."""
        class _Old:
            w1_estimate = 1.5
            class grade:
                value = "RELIABLE"
        assert _cid_supports_r4(_Old(), 0.1) is False

    def test_cid_for_unrelated_edge_is_ignored(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED")])
        m = {"A": _series(30), "B": _series(50)}
        res = compute_ebd(m, {"A": B, "B": B}, pag, WINDOW,
                          cid_results={"X→Y": self._CID()})
        assert _by(res, "A").r4_pass is False


class TestConfidenceAndAbstention:
    def test_bidirected_adjacent_candidate_flagged_not_identifiable(self):
        pag = _pag(["A", "B"], [("A", "B", "DIRECTED"), ("A", "B", "BIDIRECTED")])
        res = compute_ebd({"A": _series(30), "B": _series(50)}, {"A": B, "B": B}, pag, WINDOW)
        a = _by(res, "A")
        assert a.identifiability_state == "NOT_IDENTIFIABLE"
        assert a.evidence_type == "OBSERVATIONAL"

    def test_e2e_abstention_rule_on_not_identifiable(self):
        """The e2e runner must abstain on NOT_IDENTIFIABLE top candidates lacking R4.
        Source-level check (the runner needs a live stack to execute)."""
        src = (Path(__file__).resolve().parents[2] / "src/rift/pipeline/e2e_runner.py").read_text()
        assert 'identifiability_state == "NOT_IDENTIFIABLE"' in src


# ───────────────────────────── Label-leakage regression ─────────────────────────────

class TestNoGroundTruthLeakage:
    @staticmethod
    def _eval_mod():
        root = Path(__file__).resolve().parents[2]
        for p in (root / "scripts", root):
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
        import run_reproducible_evaluation as mod
        return mod

    def test_learned_outcome_node_ignores_affected_services_label(self):
        mod = self._eval_mod()
        pag = _pag(["A", "B", "C"], [("A", "B", "DIRECTED"), ("B", "C", "DIRECTED")])
        m = {"A": _series(20), "B": _series(30), "C": _series(40)}
        ebd = compute_ebd(m, {k: B for k in m}, pag, WINDOW)
        poisoned = {"affected_services": ["A", "WRONG_LABEL"]}
        node = mod.select_outcome_node(ebd, "A", poisoned, use_oracle_pag=False)
        assert node == "C"
        # oracle variant is explicitly allowed to use the label
        assert mod.select_outcome_node(ebd, "A", poisoned, use_oracle_pag=True) == "WRONG_LABEL"

    def test_ebd_signature_has_no_label_inputs(self):
        import inspect
        params = set(inspect.signature(compute_ebd).parameters)
        assert not params & {"root_cause_service", "ground_truth", "scenario", "affected_services",
                             "injected_at_t", "causal_path"}
