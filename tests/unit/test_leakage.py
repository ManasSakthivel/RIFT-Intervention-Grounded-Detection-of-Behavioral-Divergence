"""Tests for held-out leakage detection — Phase 3.6 §19."""
from __future__ import annotations

import pytest
from src.rift.evaluation.held_out_guard import HeldOutGuard, HeldOutLeakageError


class TestLeakageDetection:

    def test_no_access_without_token(self):
        guard = HeldOutGuard()
        with pytest.raises(HeldOutLeakageError):
            guard.check_access("baseline_run")

    def test_access_log_records_unauthorized(self):
        guard = HeldOutGuard()
        try:
            guard.check_access("tuning_code")
        except HeldOutLeakageError:
            pass
        log = guard.get_access_log()
        assert len(log) == 1
        assert not log[0]["authorized"]

    def test_access_log_records_authorized(self):
        guard = HeldOutGuard()
        guard.allow_oracle("FINAL_EVAL_TOKEN")
        guard.activate_token("FINAL_EVAL_TOKEN")
        guard.check_access("oracle_eval")
        guard.deactivate_token()
        log = guard.get_access_log()
        assert log[0]["authorized"]

    def test_assert_no_unauthorized_fails_with_leakage(self):
        guard = HeldOutGuard()
        try:
            guard.check_access("leak")
        except HeldOutLeakageError:
            pass
        with pytest.raises(AssertionError, match="LEAKAGE"):
            guard.assert_no_unauthorized_access()

    def test_assert_no_unauthorized_passes_clean(self):
        guard = HeldOutGuard()
        # No access attempted
        guard.assert_no_unauthorized_access()  # should not raise
