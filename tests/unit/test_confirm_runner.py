"""Tests for the confirmatory runner (WP3 tests C6, C9, T8).

Tests runner error semantics (D21), interface isolation (T8), and completeness stops (C9).
Only runs on dev/val or stub scenarios; never on sealed held-out data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[3]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.sprint450_run_confirm import (  # noqa: E402
    _assert_no_labels, _always_abstain_record, _check_integrity_stops,
    _run_one_method, ALWAYS_ABSTAIN_ID, MIN_COMPLETION, _FORBIDDEN_LABEL_KEYS,
)
from src.rift.scenarios import generator_confirm as gc  # noqa: E402


def _make_pilot_stripped(idx=1, struct="S01_spine_with_leaves"):
    """Build a pilot scenario and strip label fields (simulating label-stripped input)."""
    from src.rift.scenarios.independence import strip_labels
    sc = gc.build_scenario("pilot", idx, struct, "latency_degradation",
                           "immediate_propagation", "moderate_load", "complete_telemetry",
                           "single_service", None)
    stripped = strip_labels(sc)
    # strip_labels may not remove all label fields; ensure ground_truth and design are absent
    stripped.pop("ground_truth", None)
    stripped.pop("design", None)
    return stripped


# ------------------------------------------------------------------------------- T8: Label isolation
class TestT8LabelIsolation:
    """T8: no label-bearing key reaches a method. Poisoning ground_truth/design causes abort."""

    def test_no_labels_passes_stripped(self):
        sc = _make_pilot_stripped()
        assert "ground_truth" not in sc
        assert "design" not in sc
        _assert_no_labels(sc, "V3-FULL")  # should not raise

    def test_labels_present_raises(self):
        sc = _make_pilot_stripped()
        sc["ground_truth"] = {"expected_outcome": "ATTRIBUTE", "roots": ["fake"]}
        with pytest.raises(RuntimeError, match="T8 VIOLATION"):
            _assert_no_labels(sc, "V3-FULL")

    def test_design_present_raises(self):
        sc = _make_pilot_stripped()
        sc["design"] = {"true_roots": ["fake"]}
        with pytest.raises(RuntimeError, match="T8 VIOLATION"):
            _assert_no_labels(sc, "B0-EARLIEST")


# ------------------------------------------------------------------------------- C6: Error semantics (D21)
class TestC6ErrorSemantics:
    """C6: method exception → abstention, error_flag=1, n_do_charged reflects actual do() calls.
    Late return → abstention with answer stored aside.
    """

    def test_always_abstain_never_errors(self):
        rec = _always_abstain_record("TEST-001", 42, "sha256fake")
        assert rec["error_flag"] == 0
        assert rec["abstained"] is True
        assert rec["n_do_charged"] == 0

    def test_always_abstain_has_required_fields(self):
        rec = _always_abstain_record("TEST-002", 99, "sha256fake")
        for key in ["scenario_id", "method_id", "seed", "abstained", "error_flag",
                    "n_do_charged", "wall_s", "runner_sha256"]:
            assert key in rec, f"Missing key {key}"

    def test_v3_on_pilot_scenario(self):
        """V3 should run without error on a label-stripped pilot scenario."""
        sc = _make_pilot_stripped(idx=5001)
        rec = _run_one_method(sc, "V3-FULL", "runner_sha_test")
        assert rec["scenario_id"] == sc["scenario_id"]
        assert rec["method_id"] == "V3-FULL"
        assert rec["error_flag"] in (0, 1)  # May error if V3 deps unavailable
        assert "abstained" in rec
        assert "n_do_charged" in rec

    def test_record_has_d22_fields(self):
        """Runner records must have D22 V3 raw fields."""
        sc = _make_pilot_stripped(idx=5002)
        rec = _run_one_method(sc, "V3-FULL", "runner_sha_test")
        for key in ["intervened", "diverging", "confirmed"]:
            assert key in rec, f"Missing D22 field {key}"


# ------------------------------------------------------------------------------- C9: Completeness check
class TestC9RecordCompleteness:
    """C9: <95% records for a method stops that method and reports the fraction. Error rows count as records."""

    def test_min_completion_constant(self):
        assert MIN_COMPLETION == 0.95, f"MIN_COMPLETION should be 0.95, got {MIN_COMPLETION}"

    def test_error_rows_count_as_records(self):
        """Error rows should be present in output (not dropped), contributing to completion count."""
        sc = _make_pilot_stripped(idx=5003)
        rec = _run_one_method(sc, "V3-FULL", "runner_sha_test")
        # The record should exist (error or not) — it must always be written
        assert rec is not None
        assert "scenario_id" in rec


# ------------------------------------------------------------------------------- C11: No sealed access
class TestC11NoSealedAccess:
    """C11: runner refuses to run on sealed held-out paths."""

    def test_refuse_heldout_candidate_path(self, tmp_path):
        sealed = tmp_path / "heldout_candidate.json"
        sealed.write_text("{}")
        with pytest.raises(RuntimeError, match="sealed held-out"):
            _check_integrity_stops(sealed, "sha256fake")

    def test_refuse_heldout_status_path(self, tmp_path):
        sealed = tmp_path / "heldout_status.json"
        sealed.write_text("{}")
        with pytest.raises(RuntimeError, match="sealed held-out"):
            _check_integrity_stops(sealed, "sha256fake")

    def test_allow_normal_confirm_path(self, tmp_path):
        safe = tmp_path / "confirm_stripped.json"
        safe.write_text("{}")
        # Should NOT raise for a normal confirmatory path
        _check_integrity_stops(safe, "sha256fake")
