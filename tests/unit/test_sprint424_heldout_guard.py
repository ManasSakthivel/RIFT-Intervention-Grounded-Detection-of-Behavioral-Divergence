"""
Sprint 4.2.4 / Issue 3 — held-out guard: repo-root-relative resolution, hash + identity
verification, fail-closed behaviour, no dev->held-out substitution, no held-out reads during
threshold selection.

No test here names the sealed file with a quoted literal path (the sealed-gate scanner would
flag it); the filename always comes from the registry.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from src.rift.evaluation import dataset_registry as dr  # noqa: E402
from src.rift.evaluation.dataset_registry import (  # noqa: E402
    DatasetIntegrityError, HeldOutLeakageError, PURPOSE_FINAL, PURPOSE_SELECTION,
    REGISTRY, SPLIT_DEVELOPMENT, SPLIT_HELD_OUT_TEST, SPLIT_VALIDATION, load_split,
)
from src.rift.evaluation.held_out_guard import HeldOutGuard  # noqa: E402

HELD = REGISTRY[SPLIT_HELD_OUT_TEST].filename
DEV = REGISTRY[SPLIT_DEVELOPMENT].filename


def _active_guard() -> HeldOutGuard:
    g = HeldOutGuard()
    g.allow_oracle("T")
    g.activate_token("T")
    return g


@pytest.fixture()
def sandbox(tmp_path):
    """A copy of the datasets directory under tmp_path/<repo-layout>."""
    dst = tmp_path.joinpath(*dr.DATA_SUBDIR)
    shutil.copytree(dr.data_dir(), dst)
    return tmp_path


# ── correct location / CWD independence ────────────────────────────────────────────────────────

def test_correct_repo_location_resolves_and_verifies():
    p = dr.resolve_path(SPLIT_HELD_OUT_TEST)
    assert p == REPO / "datasets" / "rift_faults" / HELD
    assert dr.verify_all_files() == []
    assert len(load_split(SPLIT_DEVELOPMENT)) == 50
    assert len(load_split(SPLIT_VALIDATION)) == 18


def test_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert dr.resolve_path(SPLIT_DEVELOPMENT).is_file()
    assert len(load_split(SPLIT_DEVELOPMENT)) == 50
    assert len(load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=_active_guard())) == 15


def test_sealed_script_passes_from_other_cwd(tmp_path):
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "verify_heldout_sealed.py")],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4/4 checks passed" in r.stdout


# ── fail closed: missing / wrong hash / wrong identity ─────────────────────────────────────────

def test_missing_file_fails_closed(sandbox):
    (sandbox / "datasets" / "rift_faults" / DEV).unlink()
    with pytest.raises(DatasetIntegrityError, match="not found"):
        load_split(SPLIT_DEVELOPMENT, root=sandbox)
    assert any("MISSING" in p for p in dr.verify_all_files(sandbox))


def test_missing_sealed_file_fails_closed(sandbox):
    (sandbox / "datasets" / "rift_faults" / HELD).unlink()
    with pytest.raises(DatasetIntegrityError, match="not found"):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=_active_guard(), root=sandbox)


def test_wrong_hash_fails_closed(sandbox):
    path = sandbox / "datasets" / "rift_faults" / DEV
    data = json.loads(path.read_text())
    data["scenarios"][0]["name"] = "tampered"
    path.write_text(json.dumps(data, indent=2))
    with pytest.raises(DatasetIntegrityError, match="SHA-256 mismatch"):
        load_split(SPLIT_DEVELOPMENT, root=sandbox)
    assert dr.verify_all_files(sandbox)


def test_wrong_hash_on_sealed_file_fails_closed(sandbox):
    path = sandbox / "datasets" / "rift_faults" / HELD
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(DatasetIntegrityError):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=_active_guard(), root=sandbox)


def test_wrong_identity_with_matching_hash_fails_closed():
    """Even when bytes match their OWN pin, a file whose declared split differs from the registry
    identity is rejected (checked directly through verify_bytes with a forged spec)."""
    dev_raw = dr.resolve_path(SPLIT_DEVELOPMENT).read_bytes()
    forged = dr.DatasetSpec(SPLIT_HELD_OUT_TEST, "x", dr.sha256_bytes(dev_raw), len(dev_raw), 50)
    with pytest.raises(DatasetIntegrityError, match="wrong dataset identity"):
        dr.verify_bytes(SPLIT_HELD_OUT_TEST, dev_raw, forged)


def test_dev_substituted_for_held_out_is_rejected(sandbox):
    d = sandbox / "datasets" / "rift_faults"
    shutil.copyfile(d / DEV, d / HELD)       # substitution attempt
    with pytest.raises(DatasetIntegrityError):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=_active_guard(), root=sandbox)


def test_held_out_substituted_for_dev_is_rejected(sandbox):
    d = sandbox / "datasets" / "rift_faults"
    shutil.copyfile(d / HELD, d / DEV)
    with pytest.raises(DatasetIntegrityError):
        load_split(SPLIT_DEVELOPMENT, root=sandbox)


def test_unknown_split_and_purpose_rejected():
    with pytest.raises(DatasetIntegrityError):
        load_split("DEVELOPMENT_COPY")
    with pytest.raises(DatasetIntegrityError):
        load_split(SPLIT_DEVELOPMENT, purpose="tuning")


# ── held-out access policy ─────────────────────────────────────────────────────────────────────

def test_held_out_blocked_for_selection_even_with_active_guard():
    with pytest.raises(DatasetIntegrityError, match="sealed"):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_SELECTION, guard=_active_guard())


def test_held_out_requires_guard_and_token():
    with pytest.raises(HeldOutLeakageError):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL)
    g = HeldOutGuard()
    g.allow_oracle("T")                       # registered but NOT activated
    with pytest.raises(HeldOutLeakageError):
        load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=g)


def test_authorised_final_access_succeeds_and_is_logged():
    g = _active_guard()
    sc = load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=g)
    assert len(sc) == 15
    assert g.get_access_log()[-1]["authorized"] is True


def test_evaluate_dataset_split_held_out_without_guard_raises():
    import run_reproducible_evaluation as rre
    with pytest.raises(HeldOutLeakageError):
        rre.evaluate_dataset_split(SPLIT_HELD_OUT_TEST, "x")


# ── threshold-selection code path never touches held-out ───────────────────────────────────────

def test_threshold_selection_path_never_references_held_out():
    src = (REPO / "scripts" / "sprint423_detector_comparison.py").read_text()
    dev_fn = src[src.index("def build_dev"):src.index("def build_final")]
    sel_fn = src[src.index("def stage_select"):src.index("def _stage4_check")]
    adv_fn = src[src.index("def _adv_series"):src.index("def _stress_series")]
    for fn in (dev_fn, sel_fn, adv_fn):
        assert "HELD" not in fn.upper().replace("SHELD", "")
        assert "PURPOSE_FINAL" not in fn and "SPLIT_HELD_OUT_TEST" not in fn
    assert "build_final" not in sel_fn
    final_fn = src[src.index("def build_final"):src.index("# ───", src.index("def build_final"))]
    assert "PURPOSE_FINAL" in final_fn and "guard=guard" in final_fn


def test_no_literal_sealed_path_in_evaluator_or_comparison_script():
    for name in ("run_reproducible_evaluation.py", "sprint423_detector_comparison.py"):
        txt = (REPO / "scripts" / name).read_text()
        assert HELD not in txt, name


def test_selection_loader_has_no_route_to_sealed_split():
    """Every non-final purpose is rejected for the sealed split regardless of guard state."""
    g = _active_guard()
    for purpose in (PURPOSE_SELECTION,):
        with pytest.raises(DatasetIntegrityError):
            load_split(SPLIT_HELD_OUT_TEST, purpose=purpose, guard=g)


def test_historical_manifest_copy_pinned():
    assert dr.sha256_bytes(
        (dr.data_dir() / dr.HISTORICAL_MANIFEST_V1).read_bytes()) == dr.HISTORICAL_MANIFEST_V1_SHA256
