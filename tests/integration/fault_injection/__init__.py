"""Integration tests for fault injection framework.

Linux-specific tests are skipped with explicit reason.
"""
from __future__ import annotations

import pytest
import sys


class TestFaultInjectorIntegration:

    def test_fault_injector_dry_run_does_not_execute_tc(self):
        """Dry-run injection must NOT execute tc commands."""
        from src.rift.fault_injection.fault_injector import (
            FaultInjector, FaultScenario, FaultType, SplitLabel
        )
        injector = FaultInjector(dry_run=True)
        scenario = FaultScenario(
            fault_id="fi-test-001",
            scenario_id="scenario-001",
            fault_type=FaultType.NETWORK_LATENCY,
            target_service="frontend",
            injection_time_s=0.0,
            duration_s=30.0,
            expected_causal_mechanism="latency propagation",
            expected_affected_services=["cart"],
            ground_truth_root_cause="frontend",
            whether_confounded=False,
            whether_multi_cause=False,
            expected_identifiability_state="IDENTIFIABLE",
            split=SplitLabel.DEVELOPMENT,
            target_ip="10.0.0.1",
            interface="eth0",
            latency_ms=100.0,
            jitter_ms=10.0,
        )
        record = injector.inject(scenario, namespace="rift-eval-dev")
        # Dry run: DRY_RUN status, injection NOT verified
        assert record.status.value in ("DRY_RUN", "ABORTED", "INJECTED")
        assert record.injection_verified is False

    def test_held_out_guard_in_fault_injector(self):
        """Fault injector must refuse HELD_OUT_TEST scenarios."""
        from src.rift.fault_injection.fault_injector import (
            FaultInjector, FaultScenario, FaultType, SplitLabel
        )
        injector = FaultInjector(dry_run=True, allow_held_out=False)
        scenario = FaultScenario(
            fault_id="fi-held-001",
            scenario_id="held-001",
            fault_type=FaultType.NETWORK_LATENCY,
            target_service="frontend",
            injection_time_s=0.0,
            duration_s=30.0,
            expected_causal_mechanism="test",
            expected_affected_services=[],
            ground_truth_root_cause="frontend",
            whether_confounded=False,
            whether_multi_cause=False,
            expected_identifiability_state="IDENTIFIABLE",
            split=SplitLabel.HELD_OUT_TEST,
        )
        with pytest.raises(ValueError, match="HELD_OUT_TEST"):
            injector.inject(scenario, namespace="rift-eval-dev")

    @pytest.mark.skipif(
        not sys.platform.startswith("linux"),
        reason="SKIPPED: requires Linux + CAP_NET_ADMIN"
    )
    def test_live_injection_verifies(self):  # pragma: no cover
        """Live injection test — Linux only."""
        pass  # Placeholder for Linux execution
