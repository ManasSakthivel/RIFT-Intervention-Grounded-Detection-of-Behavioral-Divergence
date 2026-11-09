"""
Sprint 4.2.4 / Issue 1 -- Stage 4 attribution must come from pipeline inference, not a literal.

Covers: ground-truth invariance, evidence sensitivity, abstention on an unidentifiable/insufficient
case, correctness computed only after inference, and that the analysis script cannot emit a
hard-coded 1/1.
"""
import copy
import hashlib
import inspect
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult  # noqa: E402
from src.rift.pipeline import stage4_attribution as s4  # noqa: E402

SAVED = REPO / "artifacts" / "stage4_intervention_results.json"
SAVED_SHA256 = "e4cf1391c83bcb33070e8bc4ae3f8b792df2e0d1970df14524fc6c8d5d1dcffe"
SCRIPT = REPO / "scripts" / "stage4_intervention_analysis.py"


# ── fixtures ────────────────────────────────────────────────────────────────────────────────────

def _rows(vals, t0):
    return [{"t": t0 + 10.0 * i, "val": float(v) / 1000.0} for i, v in enumerate(vals)]


def synth(n_pre=30, n_act=30, shifts=None, target="rift-cartservice", seed=0, label="cartservice"):
    """Synthetic saved-record (values in ms, stored in seconds like the real artifact)."""
    shifts = {"cartservice": 50.0, "checkoutservice": 40.0, "frontend": 30.0,
              "productcatalogservice": 0.0} if shifts is None else shifts
    rng = np.random.default_rng(seed)
    rec = {"pre_baseline": {}, "intervention": {}, "post_recovery": {}, "target_service": target,
           "ground_truth": label, "attributed_root_cause": label, "attribution_accuracy_top1": 1.0,
           "verdict": "PASS", "summary_table": [{"service": "x", "diverged": True}]}
    t_pre, t_act = 1000.0, 1000.0 + 10.0 * n_pre
    for svc, sh in shifts.items():
        rec["pre_baseline"][svc] = _rows(10.0 + rng.normal(0, 1.0, n_pre), t_pre)
        rec["intervention"][svc] = _rows(10.0 + sh + rng.normal(0, 1.0, n_act), t_act)
        rec["post_recovery"][svc] = _rows(10.0 + rng.normal(0, 1.0, 5), t_act + 10.0 * n_act)
    return rec


def _chain_pag(variables):
    """cartservice -> checkoutservice -> frontend (oriented); productcatalogservice isolated."""
    edges = [PAGEdge("cartservice", "checkoutservice", PAGEdgeType.DIRECTED),
             PAGEdge("checkoutservice", "frontend", PAGEdgeType.DIRECTED)]
    return PAGResult(variables=list(variables), edges=edges, n_samples_used=60,
                     n_variables=len(variables))


@pytest.fixture()
def chain_fci(monkeypatch):
    monkeypatch.setattr(s4, "run_fci", lambda data, **kw: _chain_pag(list(data.columns)))


def real():
    return json.loads(SAVED.read_text())


# ── the historical artifact is untouched ────────────────────────────────────────────────────────

def test_historical_stage4_artifact_is_unchanged():
    assert hashlib.sha256(SAVED.read_bytes()).hexdigest() == SAVED_SHA256


# ── genuine inference on the real saved telemetry ───────────────────────────────────────────────

def test_real_stage4_telemetry_produces_honest_abstention_not_a_manufactured_success():
    r = s4.analyze_saved_record(real())
    p, e = r["prediction"], r["evaluation"]
    assert p["abstained"] is True and p["predicted_root"] is None
    assert p["abstention_reason"] == "NOT_IDENTIFIABLE"
    assert p["ebd_candidate"] == "cartservice"                       # earliest, tied; from EBD output
    assert p["causal_path_kind"] == "SEMI_DIRECTED"                  # reachability, not ancestry
    assert p["evidence_type"] == "OBSERVATIONAL"                     # R4 impossible: n_pre=15, n_act=12
    assert p["cid_grade"] == "INSUFFICIENT"
    assert e["outcome"] == "ABSTAINED" and e["top1_correct"] is None and e["coverage"] == 0.0
    assert e["n_trials"] == 1
    assert "attribution_accuracy_top1" not in r["summary"]
    assert p["detection_timestamp"] == 1793642335.0 and p["prediction_timestamp"] == 1793642445.0


def test_required_machine_readable_fields_present():
    s = s4.analyze_saved_record(real())["summary"]
    for k in ("predicted_root", "ground_truth_root", "confidence", "abstained", "ebd_candidate",
              "causal_path_kind", "evidence_type", "cid_grade", "detection_timestamp",
              "prediction_timestamp"):
        assert k in s


def test_inference_is_deterministic():
    a, b = s4.analyze_saved_record(real()), s4.analyze_saved_record(real())
    for r in (a, b):
        r.pop("computed_at_utc")
    assert a == b


# ── no ground-truth leakage ─────────────────────────────────────────────────────────────────────

class _Guarded(dict):
    """Raises if inference touches any label/result key of the saved record."""
    def _check(self, k):
        if k in s4.LABEL_KEYS:
            raise AssertionError(f"inference read label key {k!r}")

    def __getitem__(self, k):
        self._check(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self._check(k)
        return super().get(k, default)


def test_inference_never_reads_label_keys():
    rec = _Guarded(real())
    ev = s4.build_evidence(rec)
    pred = s4.infer(ev)
    assert pred.ebd_candidate == "cartservice"


def test_changing_ground_truth_labels_does_not_change_prediction():
    base = real()
    flipped = copy.deepcopy(base)
    flipped.update(ground_truth="frontend", attributed_root_cause="frontend",
                   attribution_accuracy_top1=0.0, verdict="FAIL", summary_table=[])
    a = s4.analyze_saved_record(base)
    b = s4.analyze_saved_record(flipped)
    assert a["prediction"] == b["prediction"]
    assert a["summary"]["predicted_root"] == b["summary"]["predicted_root"]
    assert a["evaluation"]["ground_truth_root"] == "cartservice"
    assert b["evaluation"]["ground_truth_root"] == "frontend"


def test_evaluation_only_argument_does_not_change_prediction(chain_fci):
    rec = synth()
    a = s4.analyze_saved_record(rec, ground_truth_root="cartservice")
    b = s4.analyze_saved_record(rec, ground_truth_root="frontend")
    assert a["prediction"] == b["prediction"]
    assert (a["evaluation"]["outcome"], b["evaluation"]["outcome"]) == ("CORRECT", "INCORRECT")


def test_adapter_and_inference_signatures_accept_no_labels():
    for fn in (s4.build_evidence, s4.infer, s4.build_cid_store):
        names = " ".join(inspect.signature(fn).parameters).lower()
        assert not re.search(r"truth|label|gt\b|expected|answer|root", names), fn.__name__
    assert "ground_truth_root" in inspect.signature(s4.evaluate_prediction).parameters


def test_evidence_does_not_depend_on_label_keys():
    a, b = real(), real()
    for k in s4.LABEL_KEYS:
        b.pop(k, None)
    ea, eb = s4.build_evidence(a), s4.build_evidence(b)
    assert ea.incident_window == eb.incident_window and ea.baselines == eb.baselines
    assert set(ea.metrics) == set(eb.metrics)


# ── evidence sensitivity ────────────────────────────────────────────────────────────────────────

def test_known_injected_target_alone_cannot_produce_an_attribution():
    """Target is declared but no service shows any divergence -> no attribution."""
    rec = synth(shifts={k: 0.0 for k in ("cartservice", "checkoutservice", "frontend",
                                         "productcatalogservice")})
    pred = s4.analyze_saved_record(rec)["prediction"]
    assert pred["abstained"] is True and pred["predicted_root"] is None
    assert pred["abstention_reason"] == "NO_CANDIDATES"


def test_removing_the_cartservice_divergence_changes_the_ebd_candidate():
    base = s4.analyze_saved_record(real())["prediction"]
    rec = real()
    # replace the active-phase cartservice series by its own baseline values (evidence change only)
    pre = rec["pre_baseline"]["cartservice"]
    rec["intervention"]["cartservice"] = [
        {"t": a["t"], "val": pre[i % len(pre)]["val"]} for i, a in enumerate(rec["intervention"]["cartservice"])]
    out = s4.analyze_saved_record(rec)["prediction"]
    assert base["ebd_candidate"] == "cartservice"
    assert out["ebd_candidate"] != "cartservice"
    assert "cartservice" not in out["diverging_services"]


def test_prediction_follows_evidence_not_the_declared_target(chain_fci):
    rec = synth()                                       # target = cartservice, cart diverges
    assert s4.analyze_saved_record(rec)["prediction"]["predicted_root"] == "cartservice"
    # same declared target, but the target's telemetry shows no divergence: evidence changed
    rec2 = synth(shifts={"cartservice": 0.0, "checkoutservice": 40.0, "frontend": 30.0,
                         "productcatalogservice": 0.0})
    p2 = s4.analyze_saved_record(rec2)["prediction"]
    assert p2["predicted_root"] != "cartservice"
    assert "cartservice" not in p2["diverging_services"]
    assert p2["evidence_type"] == "OBSERVATIONAL"       # no CID support for a non-diverging target


def test_missing_telemetry_for_target_gives_no_interventional_evidence(chain_fci):
    rec = synth()
    del rec["intervention"]["cartservice"]
    ev = s4.build_evidence(rec)
    assert ev.intervention is None and any("missing telemetry" in n or "no usable" in n for n in ev.notes) or \
        "cartservice" not in ev.metrics
    pred = s4.infer(ev)
    assert pred.evidence_type == "OBSERVATIONAL"


def test_too_little_evidence_abstains():
    rec = synth(n_pre=2, n_act=1)
    pred = s4.analyze_saved_record(rec)["prediction"]
    assert pred["abstained"] and pred["abstention_reason"] == "INSUFFICIENT_EVIDENCE"
    assert s4.analyze_saved_record({})["prediction"]["abstention_reason"] == "INSUFFICIENT_EVIDENCE"


def test_graph_discovery_failure_abstains_without_oracle_fallback(monkeypatch):
    def boom(*a, **k):
        raise ValueError("singular")
    monkeypatch.setattr(s4, "run_fci", boom)
    pred = s4.analyze_saved_record(synth())["prediction"]
    assert pred["abstained"] and pred["abstention_reason"].startswith("GRAPH_DISCOVERY_FAILURE")
    assert pred["predicted_root"] is None


# ── unidentifiable -> abstention ────────────────────────────────────────────────────────────────

def test_bidirected_pair_is_unidentifiable_and_abstains(monkeypatch):
    """R3 passes via a semi-directed (undirected) edge, but the identifiability module sees only a
    bidirected hidden-confounder pair -> NOT_IDENTIFIABLE -> abstention (mirrors the real data)."""
    def pag(data, **kw):
        v = list(data.columns)
        return PAGResult(variables=v, n_samples_used=60, n_variables=len(v), edges=[
            PAGEdge("cartservice", "frontend", PAGEdgeType.UNDIRECTED),
            PAGEdge("cartservice", "frontend", PAGEdgeType.BIDIRECTED)])
    monkeypatch.setattr(s4, "run_fci", pag)
    rec = synth(shifts={"cartservice": 50.0, "frontend": 60.0, "checkoutservice": 0.0,
                        "productcatalogservice": 0.0})
    r = s4.analyze_saved_record(rec)
    pred = r["prediction"]
    assert pred["abstained"] is True and pred["predicted_root"] is None
    assert pred["abstention_reason"] == "NOT_IDENTIFIABLE"
    assert pred["identifiability"]["status"] == "NOT_IDENTIFIABLE"
    assert pred["ebd_candidate"] == "cartservice"        # the candidate is reported, not promoted
    assert pred["causal_path_kind"] == "SEMI_DIRECTED"
    assert r["evaluation"]["outcome"] == "ABSTAINED"


# ── correctness is computed from real inference output ──────────────────────────────────────────

def test_correct_prediction_is_computed_after_inference(chain_fci):
    r = s4.analyze_saved_record(synth(), ground_truth_root="cartservice")
    p, e = r["prediction"], r["evaluation"]
    assert p["abstained"] is False and p["predicted_root"] == "cartservice"
    assert p["causal_path_kind"] == "DIRECTED"
    assert p["ebd_candidate_confidence"] in ("CANDIDATE", "DEFINITIVE")
    assert e["outcome"] == "CORRECT" and e["top1_correct"] is True
    # an incorrect label scored against the SAME prediction is INCORRECT -> correctness is a comparison
    assert s4.evaluate_prediction(s4.infer(s4.build_evidence(synth())), "frontend")["outcome"] == "INCORRECT"


def test_sufficient_real_cid_evidence_yields_definitive_interventional_attribution(chain_fci):
    r = s4.analyze_saved_record(synth(n_pre=30, n_act=30))
    p = r["prediction"]
    assert p["cid_grade"] in ("CANDIDATE", "RELIABLE")
    assert p["ebd_candidate_confidence"] == "DEFINITIVE" and p["evidence_type"] == "INTERVENTIONAL"
    assert p["confidence"] == pytest.approx(0.95)
    assert any(v["permutation_significant"] and v["exceeds_threshold"] for v in p["cid_evidence"].values())


def test_without_an_intervention_record_evidence_stays_observational(chain_fci):
    rec = synth()
    rec["target_service"] = None
    p = s4.analyze_saved_record(rec)["prediction"]
    assert p["evidence_type"] == "OBSERVATIONAL" and p["ebd_candidate_confidence"] == "CANDIDATE"
    assert p["cid_grade"] == "NOT_AVAILABLE"


def test_insufficient_sample_cid_never_upgrades_to_definitive(chain_fci):
    p = s4.analyze_saved_record(synth(n_pre=15, n_act=12))["prediction"]
    assert p["cid_grade"] == "INSUFFICIENT"
    assert p["ebd_candidate_confidence"] == "CANDIDATE" and p["evidence_type"] == "OBSERVATIONAL"


def test_abstention_is_neither_correct_nor_incorrect():
    pred = s4.infer(s4.build_evidence(real()))
    e = s4.evaluate_prediction(pred, "cartservice")
    assert e["outcome"] == "ABSTAINED" and e["top1_correct"] is None


# ── the analysis script can no longer hard-code success ─────────────────────────────────────────

def test_analysis_script_has_no_hardcoded_attribution_or_accuracy():
    src = SCRIPT.read_text()
    assert not re.search(r"\battributed\s*=\s*[\"']", src)
    assert not re.search(r"attribution_accuracy_top1[\"']?\]?\s*=\s*1(\.0)?\b", src)
    assert "record[\"attributed_root_cause\"]" not in src and 'record["ground_truth"]' not in src
    assert "analyze_saved_record" in src
    # the label exists only as an evaluation-only constant passed to evaluation, not to build_evidence
    assert src.count("EVALUATION_ONLY") >= 2


def test_analysis_script_cannot_report_one_of_one_from_the_target_alone():
    sys.path.insert(0, str(REPO / "scripts"))
    import stage4_intervention_analysis as script
    out = script.attribute(real())
    assert out["summary"]["abstained"] is True
    assert out["evaluation"]["outcome"] == "ABSTAINED"
    flat = synth(shifts={k: 0.0 for k in ("cartservice", "checkoutservice", "frontend",
                                          "productcatalogservice")})
    out2 = script.attribute(flat)
    assert out2["evaluation"]["outcome"] == "ABSTAINED" and out2["summary"]["predicted_root"] is None


def test_offline_script_writes_new_artifact_and_leaves_historical_input_alone(tmp_path):
    import subprocess
    out = tmp_path / "res.json"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "sprint424_stage4_offline_attribution.py"),
                        "--output", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    res = json.loads(out.read_text())
    assert res["summary"]["abstained"] is True
    assert res["inputs"]["source_artifact_sha256"] == SAVED_SHA256
    assert hashlib.sha256(SAVED.read_bytes()).hexdigest() == SAVED_SHA256
    bad = subprocess.run([sys.executable, str(REPO / "scripts" / "sprint424_stage4_offline_attribution.py"),
                          "--output", str(SAVED)], capture_output=True, text=True)
    assert bad.returncode != 0 and hashlib.sha256(SAVED.read_bytes()).hexdigest() == SAVED_SHA256


# ── learned variant of the batch evaluator must not fall back to the ORACLE PAG ─────────────────

def test_learned_rift_full_does_not_fall_back_to_oracle_pag_on_fci_failure(monkeypatch):
    sys.path.insert(0, str(REPO / "scripts"))
    import run_reproducible_evaluation as rre
    from src.rift.baselines import IncidentContext
    sc = {"fault_id": "T", "root_cause_service": "cart", "causal_path": [["cart", "checkout"]],
          "confounded": False, "affected_services": ["cart", "checkout"], "injected_at_t": 60.0}
    ctx = IncidentContext(fault_id="T", incident_window=(0.0, 180.0),
                          metrics=rre.generate_scenario_metrics(sc, ["cart", "checkout", "frontend"], 10.0, seed=1),
                          baseline_stats={}, call_graph=rre.build_call_graph())

    def boom(*a, **k):
        raise ValueError("singular")
    called = []
    monkeypatch.setattr(rre, "run_fci", boom)
    monkeypatch.setattr(rre, "build_oracle_pag", lambda s: called.append(1))
    out = rre.run_rift_full_scenario(sc, ctx, use_oracle_pag=False)
    assert out.abstained and out.abstention_reason.startswith("FCI_FAILED") and not called
