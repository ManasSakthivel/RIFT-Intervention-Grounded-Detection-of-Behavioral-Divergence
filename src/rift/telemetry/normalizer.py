"""RIFT Telemetry Normalization and Time Alignment — Phase 3.6 §3.

Converts raw metric streams from Prometheus/OTEL into aligned time-window
DataFrames ready for G_T construction.

The normalization pipeline:
  1. Parse raw Prometheus range-query JSON
  2. Align to Δt=10s grid (forward-fill within 1 window, then NaN)
  3. Tag collection lag
  4. Assign window_id
  5. Validate no silent imputation (NaN = missing, not 0)

Authority: docs/telemetry/ARCHITECTURE.md, docs/formal_model.md §D
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DELTA_T: float = 10.0          # seconds — frozen in spec
MAX_FORWARD_FILL_WINDOWS: int = 1      # only fill 1 consecutive missing window
VALID_METRIC_NAMES = frozenset({
    "lat_p99", "lat_p50", "err_rate", "rps", "cpu_pct", "mem_pct"
})


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class RawPrometheusMetric:
    """
    Single Prometheus range-query result for one metric+service pair.

    values: list of [unix_timestamp_float, value_str] pairs (Prometheus format)
    """
    service_id: str
    metric_name: str
    values: List[Tuple[float, str]]   # [(ts, value_str), ...]
    collection_lag_s: float = 0.0     # time between measurement and scrape receipt


@dataclass
class AlignedMetricStream:
    """
    Aligned, validated metric stream for one service+metric pair.

    Missing values are represented as NaN — never silently imputed as 0.
    Authority: docs/formal_model.md §D — missing data policy.
    """
    service_id: str
    metric_name: str
    window_ids: List[int]
    t_starts: List[float]
    values: List[Optional[float]]     # None / NaN for missing windows
    collection_lag_s: float
    n_missing: int = 0
    n_imputed: int = 0                # must remain 0 (no imputation)
    alignment_warnings: List[str] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Return a DataFrame(window_id, time, value) with NaN for missing."""
        return pd.DataFrame({
            "window_id": self.window_ids,
            "time": self.t_starts,
            "value": [float(v) if v is not None else float("nan") for v in self.values],
        })


# ---------------------------------------------------------------------------
# Normalization logic
# ---------------------------------------------------------------------------

def _parse_prometheus_value(s: str) -> Optional[float]:
    """Parse Prometheus value string. Returns None for 'NaN', '+Inf', '-Inf'."""
    try:
        v = float(s)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def align_metric_to_windows(
    raw: RawPrometheusMetric,
    t_grid_start: float,
    t_grid_end: float,
    delta_t: float = DEFAULT_DELTA_T,
    max_forward_fill: int = MAX_FORWARD_FILL_WINDOWS,
) -> AlignedMetricStream:
    """
    Align a raw Prometheus metric stream to a Δt=10s window grid.

    Alignment rules (docs/formal_model.md §D):
    - Each window [t_start, t_start+Δt) takes the LAST observation within
      the window (to match Prometheus step-query semantics).
    - If a window has no observation and the previous window was valid:
      forward-fill for at most max_forward_fill consecutive windows.
    - If a window has no observation and max_forward_fill is exhausted: NaN.
    - NaN is NEVER replaced with 0.0.

    Parameters
    ----------
    raw           : raw Prometheus metric
    t_grid_start  : unix epoch start of alignment grid
    t_grid_end    : unix epoch end (exclusive)
    delta_t       : window size in seconds (default 10.0)
    max_forward_fill : max consecutive forward-fill windows

    Returns
    -------
    AlignedMetricStream
    """
    warnings_list: List[str] = []

    # Build grid
    n_windows = max(1, int((t_grid_end - t_grid_start) / delta_t))
    window_starts = [t_grid_start + i * delta_t for i in range(n_windows)]

    # Parse raw values to (ts, float | None)
    parsed: List[Tuple[float, Optional[float]]] = []
    for ts, val_str in raw.values:
        v = _parse_prometheus_value(val_str)
        parsed.append((float(ts), v))

    # Sort by timestamp
    parsed.sort(key=lambda x: x[0])

    # For each window: find last observation within [t_start, t_start+delta_t)
    window_values: List[Optional[float]] = []
    for ws in window_starts:
        we = ws + delta_t
        window_obs = [v for ts, v in parsed if ws <= ts < we and v is not None]
        if window_obs:
            window_values.append(window_obs[-1])
        else:
            window_values.append(None)

    # Apply forward-fill (max max_forward_fill consecutive)
    filled_values: List[Optional[float]] = list(window_values)
    consecutive_fill = 0
    for i in range(1, len(filled_values)):
        if filled_values[i] is None and filled_values[i - 1] is not None:
            if consecutive_fill < max_forward_fill:
                filled_values[i] = filled_values[i - 1]
                consecutive_fill += 1
                warnings_list.append(
                    f"Window {i} (t={window_starts[i]:.0f}): forward-filled from "
                    f"window {i-1}. Fill count={consecutive_fill}."
                )
            else:
                consecutive_fill = 0
        elif filled_values[i] is not None:
            consecutive_fill = 0

    n_missing = sum(1 for v in filled_values if v is None)
    if n_missing > 0:
        warnings_list.append(
            f"{n_missing}/{n_windows} windows are NaN (no forward-fill available). "
            "Missing values are NOT imputed as 0. "
            "Authority: docs/formal_model.md §D missing data policy."
        )

    return AlignedMetricStream(
        service_id=raw.service_id,
        metric_name=raw.metric_name,
        window_ids=list(range(n_windows)),
        t_starts=window_starts,
        values=filled_values,
        collection_lag_s=raw.collection_lag_s,
        n_missing=n_missing,
        n_imputed=0,   # RIFT never imputes
        alignment_warnings=warnings_list,
    )


def normalize_telemetry_batch(
    raw_metrics: List[RawPrometheusMetric],
    t_start: float,
    t_end: float,
    delta_t: float = DEFAULT_DELTA_T,
    max_forward_fill: int = MAX_FORWARD_FILL_WINDOWS,
) -> Dict[str, Dict[str, AlignedMetricStream]]:
    """
    Normalize a batch of raw Prometheus metrics.

    Returns:
        {service_id: {metric_name: AlignedMetricStream}}

    Missing data policy: NaN is preserved. Silent imputation is forbidden.
    Authority: docs/formal_model.md §D
    """
    result: Dict[str, Dict[str, AlignedMetricStream]] = {}

    for raw in raw_metrics:
        aligned = align_metric_to_windows(
            raw, t_start, t_end, delta_t, max_forward_fill
        )
        if raw.service_id not in result:
            result[raw.service_id] = {}
        result[raw.service_id][raw.metric_name] = aligned

    return result


def to_pipeline_dataframes(
    aligned: Dict[str, Dict[str, AlignedMetricStream]],
    metric_name: str = "lat_p99",
) -> Dict[str, pd.DataFrame]:
    """
    Convert aligned metric streams to the {service: DataFrame(time, value)}
    format expected by the RIFT pipeline.

    Parameters
    ----------
    aligned     : output of normalize_telemetry_batch
    metric_name : which metric to extract (default lat_p99)

    Returns
    -------
    {service_id: DataFrame(columns=['time', 'value'])}
    """
    result: Dict[str, pd.DataFrame] = {}
    for svc, metrics in aligned.items():
        if metric_name in metrics:
            result[svc] = metrics[metric_name].to_dataframe()[["time", "value"]]
    return result
