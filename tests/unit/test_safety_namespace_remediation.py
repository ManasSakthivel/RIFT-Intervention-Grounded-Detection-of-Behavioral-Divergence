"""Unit tests for SafetyController and LinuxTcNetemBackend namespace remediation (F-01, F-02).

Status: IMPLEMENTED / NON-PRIVILEGED / VERIFIED
"""
import pytest
from unittest.mock import MagicMock, patch

from src.rift.safety.safety import (
    SafetyController,
    SafetyDecision,
    HardStopReason,
)
from src.rift.intervention.backends.linux_tc_netem import LinuxTcNetemBackend
from src.rift.optimizer.cost_model import InterventionCandidate, InterventionCost


def _make_candidate_and_cost():
    cand = InterventionCandidate("frontend", "frontend.latency", "LATENCY", 200.0, 50.0)
    cost = InterventionCost(
        candidate=cand, blast_radius=0.05, sla_impact=0.005,
        execution_duration_s=30.0, rollback_cost=5.0,
        eig=0.5, eig_normalized=0.5, safety_compliance=0.9,
        cost_composite=0.3, utility=0.4, authorized=True,
        authorization_level="AUTONOMOUS",
    )
    return cand, cost


def test_safety_missing_namespace_triggers_hard_stop():
    sc = SafetyController(approved_namespaces=["rift-eval-default"])
    cand, cost = _make_candidate_and_cost()

    assess = sc.assess_pre_intervention(cand, cost, namespace="", cumulative_ed=0.0)
    assert assess.decision == SafetyDecision.SAFE_ABORT
    assert assess.hard_stop_reason == HardStopReason.PRODUCTION_NAMESPACE


def test_safety_host_namespace_triggers_hard_stop():
    sc = SafetyController(approved_namespaces=["rift-eval-default"])
    cand, cost = _make_candidate_and_cost()

    for host_ns in ["host", "root", "default", "/proc/1/ns/net"]:
        assess = sc.assess_pre_intervention(cand, cost, namespace=host_ns, cumulative_ed=0.0)
        assert assess.decision == SafetyDecision.SAFE_ABORT
        assert assess.hard_stop_reason == HardStopReason.PRODUCTION_NAMESPACE


def test_safety_valid_evaluation_namespace_passes():
    sc = SafetyController(
        approved_namespaces=["rift-eval-default"],
        approved_targets={"frontend"},
    )
    cand, cost = _make_candidate_and_cost()

    assess = sc.assess_pre_intervention(cand, cost, namespace="rift-eval-default", cumulative_ed=0.0)
    assert assess.decision == SafetyDecision.APPROVED_AUTONOMOUS
    assert assess.hard_stop_reason is None


def test_linux_backend_rejects_host_pid():
    with pytest.raises(ValueError, match="targeting host PID namespace is forbidden"):
        LinuxTcNetemBackend(container_pid=1)


def test_linux_backend_rejects_host_namespace_string():
    with pytest.raises(ValueError, match="targeting host namespace is forbidden"):
        LinuxTcNetemBackend(sandbox_namespace="host")


def test_linux_backend_rejects_host_netns_path():
    with pytest.raises(ValueError, match="targeting host namespace descriptor is forbidden"):
        LinuxTcNetemBackend(netns_path="/proc/1/ns/net")


def test_linux_backend_wrap_ns_with_pid():
    backend = LinuxTcNetemBackend(container_pid=12345)
    wrapped = backend._wrap_ns(["tc", "qdisc", "show"])
    assert wrapped == ["nsenter", "-t", "12345", "-n", "tc", "qdisc", "show"]


def test_linux_backend_wrap_ns_with_netns_path():
    backend = LinuxTcNetemBackend(netns_path="/proc/12345/ns/net")
    wrapped = backend._wrap_ns(["tc", "qdisc", "show"])
    assert wrapped == ["nsenter", "--net=/proc/12345/ns/net", "tc", "qdisc", "show"]


def test_linux_backend_wrap_ns_fails_closed_without_target():
    backend = LinuxTcNetemBackend()
    with pytest.raises(ValueError, match="Host network namespace intervention forbidden"):
        backend._wrap_ns(["tc", "qdisc", "show"])
