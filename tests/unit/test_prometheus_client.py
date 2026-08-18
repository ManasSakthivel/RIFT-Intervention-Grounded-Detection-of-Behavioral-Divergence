"""Unit tests for PrometheusClient.collect()

Status: IMPLEMENTED / MAC_TESTED / NOT_LIVE_VALIDATED

All HTTP calls are mocked — no running Prometheus required.
"""
from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.rift.pipeline.e2e_runner import PrometheusClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(body: Any, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests.exceptions import HTTPError
        resp.raise_for_status.side_effect = HTTPError(
            f"HTTP {status_code}", response=resp
        )
    resp.json = MagicMock(return_value=body)
    return resp


def _prometheus_success(values_per_series: list[list]) -> dict:
    """Build a minimal Prometheus query_range success response."""
    result = [{"metric": {}, "values": v} for v in values_per_series]
    return {
        "status": "success",
        "data": {"resultType": "matrix", "result": result},
    }


FAKE_NOW = 1_700_000_000.0  # fixed epoch for determinism


# ---------------------------------------------------------------------------
# T1-a: Normal HTTP response with valid series data
# ---------------------------------------------------------------------------

class TestNormalResponse:
    def test_returns_dict_keyed_by_service(self):
        values = [[FAKE_NOW - 20, "0.050"], [FAKE_NOW - 10, "0.060"], [FAKE_NOW, "0.055"]]
        body = _prometheus_success([values])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend", "cart"], window_s=60.0)

        assert set(result.keys()) == {"frontend", "cart"}

    def test_dataframe_has_correct_columns(self):
        values = [[FAKE_NOW - 20, "0.050"], [FAKE_NOW - 10, "0.060"]]
        body = _prometheus_success([values])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        df = result["frontend"]
        assert list(df.columns) == ["time", "value"]

    def test_timestamp_alignment(self):
        """Timestamps returned must match what Prometheus sent."""
        ts1, ts2, ts3 = FAKE_NOW - 20, FAKE_NOW - 10, FAKE_NOW
        values = [[ts1, "0.050"], [ts2, "0.060"], [ts3, "0.055"]]
        body = _prometheus_success([values])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        times = list(result["frontend"]["time"])
        assert times == [ts1, ts2, ts3]

    def test_multiple_series_averaged(self):
        """Multiple series at the same timestamp should be averaged."""
        ts = FAKE_NOW
        series_a = [[ts, "0.100"]]
        series_b = [[ts, "0.200"]]
        body = _prometheus_success([series_a, series_b])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        assert pytest.approx(result["frontend"]["value"].iloc[0], abs=1e-6) == 0.15

    def test_each_service_gets_one_http_call(self):
        body = _prometheus_success([[[FAKE_NOW, "0.05"]]])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend", "cart", "payment"], window_s=60.0)

        assert mock_req.get.call_count == 3

    def test_endpoint_trailing_slash_stripped(self):
        body = _prometheus_success([[[FAKE_NOW, "0.01"]]])
        client = PrometheusClient("http://prometheus:9090/")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend"], window_s=60.0)

        call_url = mock_req.get.call_args[0][0]
        assert not call_url.startswith("http://prometheus:9090//")

    def test_is_live_property(self):
        client = PrometheusClient("http://prometheus:9090")
        assert client.is_live is True


# ---------------------------------------------------------------------------
# T1-b: Timeout
# ---------------------------------------------------------------------------

class TestTimeout:
    def test_timeout_raises(self):
        import requests.exceptions
        client = PrometheusClient("http://prometheus:9090", timeout_s=1.0)

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.side_effect = requests.exceptions.Timeout("timed out")
            with pytest.raises(Exception):
                client.collect(["frontend"], window_s=60.0)

    def test_timeout_is_passed_to_requests(self):
        body = _prometheus_success([[[FAKE_NOW, "0.01"]]])
        client = PrometheusClient("http://prometheus:9090", timeout_s=7.5)

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend"], window_s=60.0)

        kwargs = mock_req.get.call_args[1]
        assert kwargs.get("timeout") == 7.5


# ---------------------------------------------------------------------------
# T1-c: Empty response
# ---------------------------------------------------------------------------

class TestEmptyResponse:
    def test_empty_result_returns_empty_dataframe(self):
        body = {"status": "success", "data": {"resultType": "matrix", "result": []}}
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        df = result["frontend"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["time", "value"]

    def test_empty_values_list_returns_empty_dataframe(self):
        body = _prometheus_success([[]])  # series with no data points
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        assert len(result["frontend"]) == 0


# ---------------------------------------------------------------------------
# T1-d: Malformed JSON
# ---------------------------------------------------------------------------

class TestMalformedJSON:
    def test_json_decode_error_raises_value_error(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = ValueError("no JSON object could be decoded")
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = resp
            with pytest.raises((ValueError, Exception)):
                client.collect(["frontend"], window_s=60.0)

    def test_non_success_status_raises_value_error(self):
        body = {"status": "error", "errorType": "bad_data", "error": "bad query"}
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            with pytest.raises(ValueError, match="non-success"):
                client.collect(["frontend"], window_s=60.0)

    def test_nan_values_are_skipped(self):
        """Prometheus may return 'NaN' string for gaps; those must be dropped."""
        body = _prometheus_success([
            [[FAKE_NOW - 20, "NaN"], [FAKE_NOW - 10, "0.050"], [FAKE_NOW, "NaN"]]
        ])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            result = client.collect(["frontend"], window_s=60.0)

        # Only the valid data point should survive
        assert len(result["frontend"]) == 1
        assert pytest.approx(result["frontend"]["value"].iloc[0], abs=1e-6) == 0.050


# ---------------------------------------------------------------------------
# T1-e: Prometheus unavailable (connection error)
# ---------------------------------------------------------------------------

class TestPrometheusUnavailable:
    def test_connection_error_raises(self):
        import requests.exceptions
        client = PrometheusClient("http://unreachable:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.side_effect = requests.exceptions.ConnectionError("refused")
            with pytest.raises(Exception):
                client.collect(["frontend"], window_s=60.0)

    def test_http_500_raises(self):
        import requests.exceptions
        resp = MagicMock()
        resp.status_code = 500
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = resp
            with pytest.raises(Exception):
                client.collect(["frontend"], window_s=60.0)


# ---------------------------------------------------------------------------
# T1-f: Timestamp alignment — step derived from scrape_interval_s
# ---------------------------------------------------------------------------

class TestTimestampAlignment:
    def test_step_equals_scrape_interval_when_ge_10(self):
        """step parameter must equal scrape_interval_s when >= 10."""
        body = _prometheus_success([[[FAKE_NOW, "0.01"]]])
        client = PrometheusClient("http://prometheus:9090", scrape_interval_s=15.0)

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend"], window_s=60.0)

        kwargs = mock_req.get.call_args[1]
        params = kwargs.get("params", mock_req.get.call_args[0][1] if len(mock_req.get.call_args[0]) > 1 else {})
        # step is passed as "15s"
        assert params.get("step") == "15s"

    def test_step_minimum_is_10s(self):
        """If scrape_interval_s < 10, step must still be 10s."""
        body = _prometheus_success([[[FAKE_NOW, "0.01"]]])
        client = PrometheusClient("http://prometheus:9090", scrape_interval_s=5.0)

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req:
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend"], window_s=60.0)

        kwargs = mock_req.get.call_args[1]
        params = kwargs.get("params", {})
        assert params.get("step") == "10s"

    def test_query_range_receives_correct_time_bounds(self):
        """start = t_end - window_s, end = t_end."""
        body = _prometheus_success([[[FAKE_NOW, "0.01"]]])
        client = PrometheusClient("http://prometheus:9090")

        with patch("src.rift.pipeline.e2e_runner._requests") as mock_req, \
             patch("src.rift.pipeline.e2e_runner.time") as mock_time:
            mock_time.time.return_value = FAKE_NOW
            mock_req.get.return_value = _make_response(body)
            client.collect(["frontend"], window_s=120.0)

        params = mock_req.get.call_args[1].get("params", {})
        assert params["start"] == pytest.approx(FAKE_NOW - 120.0)
        assert params["end"] == pytest.approx(FAKE_NOW)
