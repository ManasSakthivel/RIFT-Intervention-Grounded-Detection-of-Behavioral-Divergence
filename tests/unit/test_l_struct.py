"""D23 / L-struct: proves the structural label and covariates are independent of RIFT detector thresholds.

Reads only committed dev/val (``datasets/rift_v2/{dev,val}.json``). Never touches the sealed held-out
candidate. Does not modify any dataset or result.
"""
import ast
import copy
import json
import sys
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.scenarios import generator_v2 as G  # noqa: E402
from src.rift.scenarios import l_struct as LS  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402
from src.rift.scenarios.independence import LABEL_FIELDS, strip_labels  # noqa: E402

SRC = ROOT / "src" / "rift" / "scenarios" / "l_struct.py"
FORBIDDEN_MODULE_FRAGMENTS = ("generator_v2", "ebd", "attribution_v3", "evaluation", "baselines",
                              "pipeline", "cid", "validators")
FORBIDDEN_NAMES = {"detectable_onset_window", "compute_ground_truth", "_check_r1", "theta_detect",
                   "theta_persist"}
# detector / label thresholds that must not appear as numeric literals in the label logic:
# 3.0 (onset), 4.0 (SNR gate), 30 (do() window), 45 (timing cut)
FORBIDDEN_LITERALS = {3, 4, 30, 45}
STRUCTURAL_REASONS = {"NO_FAULT", "ROOT_UNOBSERVED", "SYMMETRIC_MUTUAL_DEPENDENCY", "INSUFFICIENT_BASELINE"}


def _load(split):
    return json.load(open(ROOT / "datasets" / "rift_v2" / f"{split}.json"))["scenarios"]


@pytest.fixture(scope="module")
def corpus():
    return _load("dev") + _load("val")


def _tree():
    return ast.parse(SRC.read_text())


# ----------------------------------------------------------------- static independence
def test_imports_exclude_detector_and_label_modules():
    mods = []
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            mods.append(("." * n.level) + (n.module or ""))
            mods += [a.name for a in n.names]
    for m in mods:
        for frag in FORBIDDEN_MODULE_FRAGMENTS:
            assert frag not in m, f"l_struct imports forbidden module/name {m!r}"
    assert not (set(mods) & FORBIDDEN_NAMES)


def test_no_forbidden_identifiers():
    names = {n.id for n in ast.walk(_tree()) if isinstance(n, ast.Name)} | \
            {n.attr for n in ast.walk(_tree()) if isinstance(n, ast.Attribute)}
    assert not (names & FORBIDDEN_NAMES), names & FORBIDDEN_NAMES


def test_no_detector_threshold_numeric_literals():
    bad = [n.value for n in ast.walk(_tree())
           if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
           and not isinstance(n.value, bool) and n.value in FORBIDDEN_LITERALS]
    assert not bad, f"threshold-like literals found: {bad}"


def test_label_function_does_not_read_ground_truth_or_method_output():
    fn = next(n for n in _tree().body if isinstance(n, ast.FunctionDef) and n.name == "l_struct")
    strs = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "ground_truth" not in strs
    assert not {s for s in strs if "predict" in s or "attribut" in s.lower() and s != "STRUCTURALLY_ATTRIBUTABLE"}


def test_module_defines_no_detector_constants():
    assert not [n for n in dir(LS) if "theta" in n.lower() or "snr_gate" in n.lower()]
    assert LS.MIN_POST_REFERENCE_WINDOWS == 8


def test_does_not_reference_sealed_split():
    assert "heldout" not in SRC.read_text().lower()


# ------------------------------------------------------------ behavioural independence
def test_label_survives_removal_of_detector(monkeypatch, corpus):
    def boom(*a, **k):
        raise AssertionError("detector must not be called by L-struct")
    monkeypatch.setattr(sim, "detectable_onset_window", boom)
    monkeypatch.setattr(G, "detectable_onset_window", boom)
    for sc in corpus[:40]:
        LS.l_struct(sc)
        LS.detectability_covariates(sc)


def test_label_independent_of_frozen_ground_truth(corpus):
    for sc in corpus[:40]:
        b = copy.deepcopy(sc)
        b.pop("ground_truth")
        assert LS.l_struct(b) == LS.l_struct(sc)


def test_equals_structural_steps_of_frozen_cascade(corpus):
    """L-struct == frozen cascade steps 1-4 on every committed dev/val scenario (consistency, not relabelling)."""
    mism = [sc["scenario_id"] for sc in corpus
            if LS.l_struct(sc)["label"] != (sc["ground_truth"]["abstain_reason"] not in STRUCTURAL_REASONS)]
    assert not mism, mism


def test_label_invariant_to_signal_scale_but_primary_label_is_not(corpus):
    """Shrinking every fault amplitude must not change L-struct, while the frozen label flips."""
    flipped_primary = 0
    for sc in corpus:
        if sc["ground_truth"]["expected_outcome"] != "ATTRIBUTE":
            continue
        weak = copy.deepcopy(sc)
        for f in weak["faults"]:
            f["amp_ms"] = f["amp_ms"] * 0.05
        if G.compute_ground_truth(weak)["expected_outcome"] != "ATTRIBUTE":
            flipped_primary += 1
        assert LS.l_struct(weak) == LS.l_struct(sc)
    assert flipped_primary > 0   # the frozen label really is threshold-dependent; L-struct is not


def test_label_invariant_to_intervention_strength(corpus):
    for sc in corpus[:60]:
        w = copy.deepcopy(sc)
        w["intervention"]["magnitude_sigma"] = 0.01
        assert LS.l_struct(w) == LS.l_struct(sc)


# ------------------------------------------------------------------------- covariates
def test_covariates_are_continuous_and_span_old_thresholds(corpus):
    snr = [LS.detectability_covariates(s)["root_snr_noisefree"] for s in corpus]
    snr = [x for x in snr if x is not None]
    assert len(set(round(x, 6) for x in snr)) > 50
    assert min(snr) < 3.0 < max(snr)
    assert all(x >= 0 for x in snr)


def test_snr_covariate_scales_linearly_with_amplitude(corpus):
    for sc in corpus:
        c = LS.detectability_covariates(sc)
        if c["root_snr_noisefree"]:
            w = copy.deepcopy(sc)
            for f in w["faults"]:
                f["amp_ms"] *= 0.5
            c2 = LS.detectability_covariates(w)
            assert c2["root_snr_noisefree"] == pytest.approx(0.5 * c["root_snr_noisefree"], rel=1e-9)
            return
    pytest.fail("no scenario with positive SNR")


def test_effect_covariate_is_unthresholded_raw_quantity(corpus):
    """Interventionally-labelled scenarios have raw effect >= 1.0, but the covariate also reports < 1.0 values."""
    vals = [LS.detectability_covariates(s)["expected_do_effect_sigma"] for s in corpus]
    vals = [v for v in vals if v is not None]
    assert any(v < 1.0 for v in vals) and any(v >= 1.0 for v in vals)
    sc = next(s for s in corpus if "INTERVENTIONAL" in s["ground_truth"]["identifiable_by"])
    assert LS.detectability_covariates(sc)["expected_do_effect_sigma"] >= 1.0


# ------------------------------------------------------------------- annotate / hygiene
def test_annotate_does_not_mutate_and_fields_are_stripped(corpus):
    sc = corpus[0]
    before = json.dumps(sc, sort_keys=True)
    ann = LS.annotate(sc)
    assert json.dumps(sc, sort_keys=True) == before
    assert "label_structural" in ann["design"] and "label_structural" not in sc["design"]
    assert ann["ground_truth"] == sc["ground_truth"]          # primary label untouched
    assert "design" in LABEL_FIELDS
    stripped = json.dumps(strip_labels(ann))
    for k in LS.LABEL_ONLY_FIELDS:
        assert k not in stripped


def test_committed_datasets_not_modified_by_annotation(corpus):
    for s in corpus:
        LS.annotate(s)
    for split in ("dev", "val"):
        assert "label_structural" not in json.dumps(_load(split))
