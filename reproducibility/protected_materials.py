"""Sprint 4.4.2: transparent classification of tests that need protected local materials.

Some committed tests verify the integrity of research materials that are deliberately NOT in git:

  * the sealed Sprint 4.3.0 held-out candidate (``verify_freeze`` hashes it as one of 37 frozen files), and
  * the historical Stage 4 artifact (contains an internal host name; pinned by SHA-256).

On a fresh clone those files are absent, so the tests cannot pass and are NOT evidence of a defect. They also must
not be reported as passing. This plugin (loaded only by ``scripts/sprint442_run_tests.py``) classifies each outcome:

  REPRODUCIBLE_PASS        passed, needs only committed materials
  PROTECTED_PASS           passed, and the protected materials WERE present locally (integrity verified)
  PROTECTED_UNAVAILABLE    registered protected-material test whose required files are absent: reported as
                           UNAVAILABLE (never as passed, never silently skipped)
  FAILED                   a genuine failure (including a protected-material test that ran and failed)

It never edits frozen code or the tests themselves. Existence checks only: contents of protected files are not read.
Plain ``pytest`` (without this plugin) behaves exactly as before and reports the two failures on a fresh clone.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest

REPO = Path(__file__).resolve().parents[1]

# nodeid (as collected from the repo root) -> protected files that must exist locally for the check to be meaningful.
PROTECTED_TESTS: Dict[str, List[str]] = {
    "tests/unit/test_sprint440_attribution_v3.py::test_dev_val_pins_and_freeze_intact":
        ["datasets/rift_v2/heldout_candidate.json"],   # verify_freeze() hashes this frozen, sealed file
    "tests/unit/test_sprint440_attribution_v3.py::test_historical_stage4_artifact_untouched":
        ["artifacts/stage4_intervention_results.json"],
}

UNAVAILABLE_PREFIX = "PROTECTED-MATERIAL-UNAVAILABLE"


def missing_for(nodeid: str) -> List[str]:
    return [rel for rel in PROTECTED_TESTS.get(nodeid, []) if not (REPO / rel).is_file()]


class ProtectedMaterialPlugin:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, str]] = {}

    def pytest_collection_modifyitems(self, config, items):  # noqa: D401
        for item in items:
            miss = missing_for(item.nodeid)
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"{UNAVAILABLE_PREFIX}: {', '.join(miss)} absent (protected, not in git); integrity NOT verified"))

    def pytest_runtest_logreport(self, report):
        nid = report.nodeid
        if report.when == "setup" and report.skipped:
            reason = str(report.longrepr[2]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
            cls = "PROTECTED_UNAVAILABLE" if UNAVAILABLE_PREFIX in reason else "SKIPPED_OTHER"
            self.records[nid] = {"class": cls, "detail": reason}
        elif report.when == "call":
            if report.passed:
                cls = "PROTECTED_PASS" if nid in PROTECTED_TESTS else "REPRODUCIBLE_PASS"
            elif report.skipped:
                cls = "SKIPPED_OTHER"
            else:
                cls = "FAILED"
            self.records[nid] = {"class": cls, "detail": ""}
        elif report.when in ("setup", "teardown") and report.failed:
            self.records[nid] = {"class": "FAILED", "detail": f"{report.when} error"}

    def summary(self) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {"REPRODUCIBLE_PASS": [], "PROTECTED_PASS": [], "PROTECTED_UNAVAILABLE": [],
                                     "SKIPPED_OTHER": [], "FAILED": []}
        for nid, r in self.records.items():
            out[r["class"]].append(nid)
        return out
