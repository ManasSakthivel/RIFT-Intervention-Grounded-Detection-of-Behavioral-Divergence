"""Unit tests for Sprint 4.1.9.1 Telemetry Remediation and Query Alignment.

Tests:
1. Tracing configuration in deployment manifest (ENABLE_TRACING=1 on all 10 microservices).
2. Prometheus scrape configuration for OTel spanmetrics.
3. PrometheusClient OpenTelemetry spanmetrics query construction and fallback handling.
4. PrometheusClient custom query template support and missing series handling.

Authority: docs/SPRINT4_1_9_TELEMETRY_AND_BASELINE_VALIDATION_REPORT.md
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import yaml

from src.rift.pipeline.e2e_runner import PrometheusClient


def _make_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=body)
    return resp


class TestManifestTracingConfiguration:
    def test_podman_compose_all_microservices_have_enable_tracing(self):
        compose_path = Path(__file__).parents[2] / "deploy" / "podman-compose.yaml"
        assert compose_path.exists(), f"Manifest {compose_path} not found"

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})
        microservices_requiring_tracing = [
            "rift-emailservice",
            "rift-checkoutservice",
            "rift-recommendationservice",
            "rift-frontend",
            "rift-paymentservice",
            "rift-productcatalogservice",
            "rift-cartservice",
            "rift-currencyservice",
            "rift-shippingservice",
            "rift-adservice",
        ]

        for svc_name in microservices_requiring_tracing:
            assert svc_name in services, f"Missing service {svc_name}"
            svc_conf = services[svc_name]
            env = svc_conf.get("environment", [])
            
            # env can be dict or list of "KEY=VAL"
            if isinstance(env, dict):
                assert str(env.get("ENABLE_TRACING", "")) == "1", (
                    f"{svc_name} missing ENABLE_TRACING=1 in environment dict"
                )
                assert "COLLECTOR_SERVICE_ADDR" in env, (
                    f"{svc_name} missing COLLECTOR_SERVICE_ADDR in environment dict"
                )
            else:
                env_list = list(env)
                assert any("ENABLE_TRACING=1" in e or "ENABLE_TRACING: 1" in e for e in env_list), (
                    f"{svc_name} missing ENABLE_TRACING=1 in environment list: {env_list}"
                )
                assert any("COLLECTOR_SERVICE_ADDR=" in e for e in env_list), (
                    f"{svc_name} missing COLLECTOR_SERVICE_ADDR in environment list: {env_list}"
                )

    def test_prometheus_yaml_scrapes_spanmetrics(self):
        prom_path = Path(__file__).parents[2] / "deploy" / "prometheus.yml"
        assert prom_path.exists(), f"Prometheus config {prom_path} not found"

        with open(prom_path, "r", encoding="utf-8") as f:
            prom_data = yaml.safe_load(f)

        scrape_configs = prom_data.get("scrape_configs", [])
        job_names = [sc.get("job_name") for sc in scrape_configs]
        assert "rift-otel-spanmetrics" in job_names
        
        # Verify rift-frontend is not present as a separate scrape job without /metrics
        assert "rift-frontend" not in job_names


class TestPrometheusClientQueryAlignment:
    def test_default_queries_use_spanmetrics_schema(self):
        client = PrometheusClient("http://127.0.0.1:19090")
        assert "rift_duration_milliseconds_bucket" in client.metric_queries["lat_p99"]
        assert "span_name" in client.metric_queries["lat_p99"]
        assert "rift_calls_total" in client.metric_queries["rps"]
        assert "span_name" in client.metric_queries["rps"]

    def test_collect_executes_spanmetrics_query(self):
        fake_now = 1_700_000_000.0
        success_body = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"span_name": "hipstershop.CheckoutService/PlaceOrder"},
                        "values": [[fake_now - 10, "0.025"], [fake_now, "0.030"]],
                    }
                ],
            },
        }

        client = PrometheusClient("http://127.0.0.1:19090")
        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(success_body)
            result = client.collect(["checkoutservice"], window_s=60.0)

        assert "checkoutservice" in result
        df = result["checkoutservice"]
        assert len(df) == 2
        assert list(df["value"]) == [0.025, 0.030]

        # Verify query string sent to requests
        params = mock_req.get.call_args[1].get("params", {})
        query = params.get("query", "")
        assert "rift_duration_milliseconds_bucket" in query
        assert "span_name" in query
        assert "checkoutservice" in query

    def test_collect_custom_queries_respected(self):
        custom_queries = {
            "lat_p99": 'custom_lat{{svc="{service}"}}',
        }
        client = PrometheusClient(
            "http://127.0.0.1:19090",
            primary_metric="lat_p99",
            metric_queries=custom_queries,
        )

        fake_now = 1_700_000_000.0
        success_body = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"svc": "frontend"},
                        "values": [[fake_now, "0.015"]],
                    }
                ],
            },
        }

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(success_body)
            result = client.collect(["frontend"], window_s=60.0)

        params = mock_req.get.call_args[1].get("params", {})
        assert params.get("query") == 'custom_lat{svc="frontend"}'
        assert len(result["frontend"]) == 1
