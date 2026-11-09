"""
Sprint 4.2.4 — Issue 2: CID key schema, R4 reachability, and boundary validation.

Original failure: the E2E runner keyed CID results "{svc}→{svc}.downstream" while R4 looked up
"{src}→{tgt}" for causal-path edges, so R4/DEFINITIVE was unreachable through the pipeline.
These tests use REAL compute_cid() results (no hand-built mocks) and the REAL runner.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd
import pytest

import src.rift.pipeline.e2e_runner as e2e
from src.rift.cid.cid import CIDGrade, compute_cid
from src.rift.cid.evidence import CIDEvidenceStore, CIDKey, validate_cid_for_r4
from src.rift.ebd.ebd import compute_ebd
from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult
from src.rift.pipeline.e2e_runner import RIFTEndToEndRunner

B = {"mean": 0.0, "std": 10.0}
WINDOW = (0.0, 110.0)


# ───────────────────────────── helpers ─────────────────────────────

def _pag() -> PAGResult:
    return PAGResult(variables=["A", "B"], edges=[PAGEdge("A", "B", PAGEdgeType.DIRECTED)])


def _metrics():
    ts = [i * 10.0 for i in range(12)]
    a = pd.DataFrame({"time": ts, "value": [0.0 if t < 30 else 50.0 for t in ts]})
    b = pd.DataFrame({"time": ts, "value": [0.0 if t < 50 else 50.0 for t in ts]})
    return {"A": a, "B": b}


def _real_cid(x="A", y="B", n=60, shift=5.0, seed=0, n_post: Optional[int] = None):
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, 1.0, n)
    post = rng.normal(shift, 1.0, n_post if n_post is not None else n)
    return compute_cid(base, post, x, y, t_intervention=0.0, n_bootstrap=50, n_permutations=500)


def _run(cid_results):
    res = compute_ebd(_metrics(), {"A": B, "B": B}, _pag(), WINDOW, cid_results=cid_results)
    return next(r for r in res if r.service_id == "A")


# ───────────────────── A. valid evidence reaches R4 ─────────────────────

class TestValidCIDEvidence:
    def test_real_cid_has_all_required_fields(self):
        cid = _real_cid()
        assert cid.grade == CIDGrade.RELIABLE
        assert cid.permutation_significant is True
        assert cid.exceeds_threshold is True
        assert validate_cid_for_r4(cid, 0.1) == (True, "OK")

    def test_store_key_derived_from_result_identity(self):
        cid = _real_cid("A", "B")
        store = CIDEvidenceStore()
        assert store.add(cid) == CIDKey("A", "B")
        assert store.get("A", "B") is cid and store.get("B", "A") is None

    def test_valid_evidence_makes_definitive_reachable(self):
        store = CIDEvidenceStore()
        store.add(_real_cid("A", "B"))
        a = _run(store)
        assert a.r4_pass and a.confidence == "DEFINITIVE" and a.evidence_type == "INTERVENTIONAL"
        assert a.cid_scores["A→B"][4] == "RELIABLE"

    def test_legacy_string_key_still_accepted_at_boundary(self):
        a = _run({"A→B": _real_cid("A", "B")})
        assert a.confidence == "DEFINITIVE"

    def test_tuple_and_typed_keys_accepted(self):
        cid = _real_cid("A", "B")
        assert _run({("A", "B"): cid}).confidence == "DEFINITIVE"
        assert _run({CIDKey("A", "B"): cid}).confidence == "DEFINITIVE"


# ───────────────────── B. invalid evidence blocks DEFINITIVE ─────────────────────

class TestInvalidCIDEvidence:
    def _assert_blocked(self, a, reason_fragment=None):
        assert a.r4_pass is False
        assert a.confidence == "CANDIDATE"          # explicit non-definitive result
        assert a.evidence_type == "OBSERVATIONAL"
        if reason_fragment:
            assert any(reason_fragment in w for w in a.assumption_warnings), a.assumption_warnings

    def test_wrong_key_unrelated_pair(self):
        a = _run({CIDKey("X", "Y"): _real_cid("X", "Y")})
        self._assert_blocked(a)

    def test_wrong_direction_key(self):
        # do(B) observed on A does not confirm A as the cause
        a = _run({CIDKey("B", "A"): _real_cid("B", "A")})
        self._assert_blocked(a)

    def test_legacy_self_downstream_key_never_matches(self):
        """The exact pre-4.2.4 producer schema."""
        cid = _real_cid("A", "A.downstream")
        a = _run({"A→A.downstream": cid})
        self._assert_blocked(a)

    def test_missing_key_none_and_empty(self):
        a = _run(None)
        assert a.confidence == "CANDIDATE" and not a.r4_pass
        self._assert_blocked(_run({}))

    def test_malformed_key_rejected_with_reason(self):
        store = CIDEvidenceStore.from_mapping({"A-B": _real_cid("A", "B"), "": _real_cid("A", "B")})
        assert len(store) == 0 and len(store.rejected) == 2
        self._assert_blocked(_run({"A-B": _real_cid("A", "B")}))

    def test_key_disagreeing_with_result_identity_rejected(self):
        store = CIDEvidenceStore.from_mapping({"A→B": _real_cid("A", "C")})
        assert len(store) == 0
        assert "KEY_IDENTITY_MISMATCH" in store.rejected[0][1]
        self._assert_blocked(_run({"A→B": _real_cid("A", "C")}), "rejected at boundary")

    def test_invalid_grade_insufficient(self):
        cid = _real_cid("A", "B", n=10)
        assert cid.grade == CIDGrade.INSUFFICIENT
        self._assert_blocked(_run({CIDKey("A", "B"): cid}))
        assert validate_cid_for_r4(cid, 0.1)[1] in ("NO_W1_ESTIMATE", "GRADE_INSUFFICIENT")

    def test_insignificant_permutation(self):
        cid = _real_cid("A", "B", shift=0.0, seed=3)
        assert cid.permutation_significant is False
        self._assert_blocked(_run({CIDKey("A", "B"): cid}))

    def test_below_threshold_with_real_cid(self):
        cid = _real_cid("A", "B", shift=0.02, seed=4)
        ok, reason = validate_cid_for_r4(cid, 0.1)
        assert not ok
        self._assert_blocked(_run({CIDKey("A", "B"): cid}))

    def test_theta_override_blocks_even_valid_cid(self):
        cid = _real_cid("A", "B")
        res = compute_ebd(_metrics(), {"A": B, "B": B}, _pag(), WINDOW,
                          cid_results={CIDKey("A", "B"): cid}, theta_cid=1e6)
        a = next(r for r in res if r.service_id == "A")
        assert not a.r4_pass and a.confidence == "CANDIDATE"

    def test_missing_attributes_are_not_assumed_valid(self):
        class _Bare:
            source_variable, target_variable = "A", "B"
            w1_estimate = 9.0
        ok, reason = validate_cid_for_r4(_Bare(), 0.1)
        assert not ok and reason == "GRADE_MISSING"

    def test_non_finite_w1_rejected(self):
        class _Nan:
            w1_estimate = float("nan")
        assert validate_cid_for_r4(_Nan(), 0.1) == (False, "W1_NOT_FINITE")

    def test_evidence_for_other_intervention_does_not_confirm_candidate(self):
        # do(B) -> A is valid evidence, but candidate is A (needs do(A))
        a = _run({CIDKey("B", "A"): _real_cid("B", "A"), CIDKey("A", "C"): _real_cid("A", "C")})
        self._assert_blocked(a)

    def test_r4_cannot_rescue_failed_r1_r3(self):
        cid = _real_cid("A", "B")
        res = compute_ebd(_metrics(), {"A": B, "B": B},
                          PAGResult(variables=["A", "B"], edges=[]), WINDOW,
                          cid_results={CIDKey("A", "B"): cid})
        assert all(r.confidence != "DEFINITIVE" for r in res)


# ───────────────────── C. actual integrated E2E runner ─────────────────────

class _Telemetry:
    """Deterministic fixture. 1st collect() = incident window; later = post-intervention."""
    is_live = False

    def __init__(self, post_shift: float, seed: int = 7, null_post: bool = False):
        self.post_shift, self.seed, self.calls = post_shift, seed, 0
        self.null_post = null_post  # post window = exact replay of the pre-incident half (W1 == 0)
        self._first = None

    def collect(self, services, window_s=300.0, **kw):
        self.calls += 1
        rng = np.random.default_rng(self.seed + self.calls)
        n = int(window_s / 10)
        t = [float(i * 10) for i in range(n)]
        out = {}
        for s in services:
            v = rng.normal(50, 5, n)
            if self.calls == 1:
                if s == "A":
                    v[n // 2:] += 60
                if s == "B":
                    v[n // 2 + 2:] += 50
            elif s == "B":
                v = v + self.post_shift
            if self.calls == 1:
                pass
            elif self.null_post:
                v = self._first[s]["value"].values[: n]
            out[s] = pd.DataFrame({"time": t, "value": v})
        if self.calls == 1:
            self._first = out
            self._half = {k: d.iloc[: len(d) // 2] for k, d in out.items()}
        return out


def _runner(post_shift=400.0, post_window_s=300.0, observe_window_s=600.0, null_post=False):
    g = nx.DiGraph()
    g.add_edge("A", "B")
    g.add_node("C")
    return RIFTEndToEndRunner(_Telemetry(post_shift, null_post=null_post), ["A", "B", "C"], g, dry_run=True,
                              post_window_s=post_window_s, observe_window_s=observe_window_s)


class TestEndToEndIntegration:
    def test_valid_evidence_reaches_r4_and_definitive_without_manual_intervention(self):
        rec = _runner().run()
        cid_stage = next(s for s in rec.pipeline_stages if s.stage == "CID")
        assert cid_stage.output_summary["n_pairs"] == 6  # each do(X) x every other outcome (3 services)
        assert set(cid_stage.output_summary["grades"]) >= {"A→B", "B→A"}  # (intervened, outcome)
        assert not any(".downstream" in k for k in cid_stage.output_summary["grades"])
        a = next(e for e in rec.ebd_results if e["service_id"] == "A")
        assert a["r4_pass"] is True and a["confidence"] == "DEFINITIVE"
        assert a["evidence_type"] == "INTERVENTIONAL"
        assert rec.attribution == "A" and rec.attribution_confidence == "DEFINITIVE"
        assert rec.final_state == "PASS"
        assert rec.provenance["CID"]["schema"] == "rift.cid_evidence/1"

    def test_no_post_intervention_effect_is_not_definitive(self):
        rec = _runner(null_post=True).run()
        a = next(e for e in rec.ebd_results if e["service_id"] == "A")
        assert a["r4_pass"] is False and a["confidence"] != "DEFINITIVE"
        assert rec.attribution_confidence != "DEFINITIVE"

    def test_insufficient_samples_not_definitive(self):
        rec = _runner(post_window_s=60.0).run()  # 6 post samples -> INSUFFICIENT
        cid_stage = next(s for s in rec.pipeline_stages if s.stage == "CID")
        assert set(cid_stage.output_summary["grades"].values()) == {"INSUFFICIENT"}
        assert rec.attribution_confidence != "DEFINITIVE"
        assert all(not e["r4_pass"] for e in rec.ebd_results)

    def test_runner_source_has_no_string_built_cid_keys(self):
        import inspect
        src = inspect.getsource(e2e.RIFTEndToEndRunner.run)
        assert ".downstream" not in src
        assert 'f"{svc}→' not in src
