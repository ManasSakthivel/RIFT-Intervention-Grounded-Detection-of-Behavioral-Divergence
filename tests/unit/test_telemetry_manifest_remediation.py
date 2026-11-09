"""Unit tests for Telemetry Normalizer and Deployment Manifests (F-03, F-05, F-06).

Status: IMPLEMENTED / NON-PRIVILEGED / VERIFIED
"""
import os
import yaml
import pytest
import numpy as np

from src.rift.telemetry.normalizer import (
    align_metric_to_windows,
    normalize_telemetry_batch,
    RawPrometheusMetric,
    VALID_METRIC_NAMES,
)


def test_valid_metric_names_contains_required_metrics():
    required = {"lat_p99", "lat_p50", "err_rate", "rps", "cpu_pct", "mem_pct"}
    assert required.issubset(VALID_METRIC_NAMES)


def test_normalizer_never_silently_imputes():
    # Provide sparse raw data with a gap > 1 window
    raw = RawPrometheusMetric(
        service_id="cartservice",
        metric_name="lat_p99",
        values=[(100.0, "50.0"), (140.0, "55.0")],  # gap of 40s (4 windows of 10s)
        collection_lag_s=0.5,
    )
    stream = align_metric_to_windows(raw, t_grid_start=100.0, t_grid_end=150.0, delta_t=10.0)
    assert stream.service_id == "cartservice"
    assert stream.n_imputed == 0
    # Values array must contain NaN/None for missing windows, not 0.0
    assert any(v is None or (isinstance(v, float) and np.isnan(v)) for v in stream.values)


def test_manifest_yaml_syntax():
    manifests = [
        "deploy/podman-compose.yaml",
        "deploy/prometheus.yml",
        "deploy/otel-collector.yaml",
    ]
    for m in manifests:
        assert os.path.exists(m), f"Manifest file {m} missing"
        with open(m, "r") as f:
            data = yaml.safe_load(f)
            assert data is not None, f"Failed to parse {m}"


def test_compose_resource_limits_and_ports():
    with open("deploy/podman-compose.yaml", "r") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert len(services) == 14  # 12 boutique/redis/loadgen + otel + prometheus

    # Verify loopback-only binding for exposed ports
    for svc_name, svc in services.items():
        ports = svc.get("ports", [])
        for p in ports:
            assert p.startswith("127.0.0.1:"), f"Service {svc_name} port {p} does not bind strictly to loopback"
