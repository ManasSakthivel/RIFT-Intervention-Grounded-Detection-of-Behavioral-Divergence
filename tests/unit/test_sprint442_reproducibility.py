"""Sprint 4.4.2: tests that need ONLY committed materials, plus tests of the protected-material classifier.

These pass on a fresh clone. They verify, from committed files alone, the parts of the Sprint 4.3.0 freeze and of the
dev/val pins that do not depend on the sealed held-out file or the historical Stage 4 artifact. They do NOT replace
``test_dev_val_pins_and_freeze_intact`` / ``test_historical_stage4_artifact_untouched`` (which remain unchanged and
are reported UNAVAILABLE, not passed, when the protected files are absent). Nothing here opens the held-out split.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from reproducibility import protected_materials as pm  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import (FREEZE_FILE, PINS, load_v2, sha256_file)  # noqa: E402

PROTECTED_FREEZE_ENTRIES = {"datasets/rift_v2/heldout_candidate.json"}


def test_dev_val_load_with_pinned_hashes_from_committed_files():
    for split in ("dev", "val"):
        ls = load_v2(split)
        assert ls.sha256 == PINS[split]["sha256"]
        assert len(ls.scenarios) == PINS[split]["n"]
        assert sha256_file(ROOT / "datasets" / "rift_v2" / PINS[split]["file"]) == PINS[split]["sha256"]


def test_freeze_manifest_unprotected_entries_match_committed_files():
    """Every freeze entry other than the sealed held-out file must match. Protected entries are checked only if present."""
    fz = json.loads(FREEZE_FILE.read_text())
    files = fz["files"]
    assert len(files) == 37
    assert PROTECTED_FREEZE_ENTRIES <= set(files)
    bad = []
    for rel, want in files.items():
        if rel in PROTECTED_FREEZE_ENTRIES:
            continue
        p = ROOT / rel
        if not p.is_file() or sha256_file(p) != want:
            bad.append(rel)
    assert not bad, bad


def test_freeze_manifest_and_dev_val_are_consistent_with_dataset_manifest():
    man = json.loads((ROOT / "datasets/rift_v2/manifest.json").read_text())["datasets"]
    assert man["dev"]["sha256"] == PINS["dev"]["sha256"] and man["val"]["sha256"] == PINS["val"]["sha256"]
    fz = json.loads(FREEZE_FILE.read_text())
    assert fz["heldout_sha256"] == man["held_out"]["sha256"]          # string comparison only; held-out never opened
    assert fz["files"]["datasets/rift_v2/dev.json"] == PINS["dev"]["sha256"]
    assert fz["files"]["datasets/rift_v2/val.json"] == PINS["val"]["sha256"]


def test_sealed_and_historical_materials_are_not_tracked_in_git():
    import subprocess
    try:
        tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, stderr=subprocess.DEVNULL).decode().split("\n"))
    except Exception:  # noqa: BLE001
        pytest.skip("git metadata unavailable")
    if not tracked - {""}:
        pytest.skip("git metadata unavailable")
    for rel in ("datasets/rift_v2/heldout_candidate.json", "datasets/rift_v2/heldout_status.json",
                "artifacts/sprint4_3_0/heldout_opened.json", "artifacts/stage4_intervention_results.json"):
        assert rel not in tracked, rel
    assert not [t for t in tracked if t.startswith("artifacts/sprint4_3_0/results/held_out/")]


# ----------------------------------------------------------------------------------------- classifier behaviour
def test_registered_protected_tests_exist_in_the_v3_test_module():
    src = (ROOT / "tests/unit/test_sprint440_attribution_v3.py").read_text()
    for nid in pm.PROTECTED_TESTS:
        assert nid.split("::")[0] == "tests/unit/test_sprint440_attribution_v3.py"
        assert f"def {nid.split('::')[1]}(" in src, nid


def test_missing_for_reports_absent_protected_files(monkeypatch, tmp_path):
    nid = "tests/unit/test_sprint440_attribution_v3.py::test_historical_stage4_artifact_untouched"
    monkeypatch.setattr(pm, "REPO", tmp_path)
    assert pm.missing_for(nid) == ["artifacts/stage4_intervention_results.json"]
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/stage4_intervention_results.json").write_text("x")
    assert pm.missing_for(nid) == []
    assert pm.missing_for("tests/unit/some_other.py::test_x") == []


def test_unavailable_checks_are_never_counted_as_passed():
    plug = pm.ProtectedMaterialPlugin()

    class R:  # minimal stand-in for a pytest setup report of a skipped test
        when, skipped, passed, failed = "setup", True, False, False
        nodeid = next(iter(pm.PROTECTED_TESTS))
        longrepr = ("f", 1, f"Skipped: {pm.UNAVAILABLE_PREFIX}: x absent")

    plug.pytest_runtest_logreport(R)
    s = plug.summary()
    assert s["PROTECTED_UNAVAILABLE"] == [R.nodeid]
    assert not s["PROTECTED_PASS"] and not s["REPRODUCIBLE_PASS"] and not s["FAILED"]

    class F:
        when, skipped, passed, failed = "call", False, False, True
        nodeid = "tests/unit/x.py::test_y"
        longrepr = ""

    plug.pytest_runtest_logreport(F)
    assert plug.summary()["FAILED"] == [F.nodeid]


def test_capture_environment_records_versions_and_reads_no_protected_content(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import sprint442_capture_environment as cap
    info = cap.capture()
    assert info["packages"]["numpy"] != "NOT INSTALLED" and info["python"].count(".") == 2
    assert set(info["protected_materials_present"]) >= {"datasets/rift_v2/heldout_candidate.json"}
    assert all(set(v) == {"present"} for v in info["protected_materials_present"].values())
