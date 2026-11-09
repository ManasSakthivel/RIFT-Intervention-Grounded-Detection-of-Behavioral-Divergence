"""Unit tests for DetachedRollbackWatchdog (F-04).

Status: IMPLEMENTED / NON-PRIVILEGED / VERIFIED
"""
import pytest
from unittest.mock import MagicMock, patch

from src.rift.intervention.watchdog import (
    WatchdogSpec,
    WatchdogStatus,
    DetachedRollbackWatchdog,
)


def test_watchdog_spec_validation():
    with pytest.raises(ValueError, match="cannot target host PID"):
        WatchdogSpec(experiment_id="exp-1", target_pid=1, interface="eth0")

    with pytest.raises(ValueError, match="exceeds maximum allowed safety threshold"):
        WatchdogSpec(experiment_id="exp-1", target_pid=5000, interface="eth0", timeout_s=45.0)


def test_watchdog_dry_run_arm_and_disarm():
    watchdog = DetachedRollbackWatchdog(dry_run=True)
    spec = WatchdogSpec(experiment_id="exp-test-01", target_pid=54321, interface="eth0", timeout_s=15.0)

    record = watchdog.arm(spec)
    assert record.status == WatchdogStatus.ARMED
    assert record.watchdog_pid == 99999

    disarmed = watchdog.disarm("exp-test-01")
    assert disarmed is True
    assert record.status == WatchdogStatus.DISARMED


def test_watchdog_command_generation():
    watchdog = DetachedRollbackWatchdog(dry_run=True)
    spec = WatchdogSpec(experiment_id="exp-test-02", target_pid=12345, interface="eth0", tc_handle="1:", timeout_s=10.0)

    cmd = watchdog.generate_watchdog_command(spec)
    assert cmd[0] == "sh"
    assert cmd[1] == "-c"
    assert "sleep 10.0" in cmd[2]
    assert "nsenter -t 12345 -n" in cmd[2]
    assert "tc qdisc del dev eth0 parent 1:1 handle 1:" in cmd[2]
    assert "/proc/1/ns/net" in cmd[2]
    assert "tc qdisc del dev eth0 root handle 1:" in cmd[2]


def test_watchdog_command_includes_host_netns_avoidance():
    watchdog = DetachedRollbackWatchdog(dry_run=True)
    spec = WatchdogSpec(experiment_id="exp-test-04", target_pid=9999, interface="eth0", timeout_s=15.0)

    cmd = watchdog.generate_watchdog_command(spec)
    script = cmd[2]
    # Verify inode inequality check against host /proc/1/ns/net
    assert "stat -L -c '%i' /proc/1/ns/net" in script
    assert "stat -L -c '%i' /proc/9999/ns/net" in script


@patch("subprocess.Popen")
def test_watchdog_arm_spawns_detached_process(mock_popen):
    mock_proc = MagicMock()
    mock_proc.pid = 88888
    mock_popen.return_value = mock_proc

    watchdog = DetachedRollbackWatchdog(dry_run=False)
    spec = WatchdogSpec(experiment_id="exp-test-03", target_pid=12345, interface="eth0", timeout_s=20.0)

    record = watchdog.arm(spec)
    assert record.status == WatchdogStatus.ARMED
    assert record.watchdog_pid == 88888
    mock_popen.assert_called_once()
    assert mock_popen.call_args[1]["start_new_session"] is True
