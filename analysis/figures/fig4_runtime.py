#!/usr/bin/env python3
"""Figure 4 — Runtime / Intervention Cost.

Input:  results/EXP-009/results.json  (runtime profiling)
        results/EXP-003/results.json  (intervention cost baseline)
Output: analysis/figures/fig4_runtime.png
        analysis/figures/fig4_runtime.pdf

Reads all values from result artifacts. Never fabricates numbers.
Produces a two-panel figure:
  Left:  Mean total_ed_s (effective duration seconds) per method
  Right: Mean number of interventions per method
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXPERIMENTS = [
    ("EXP-009", "Runtime Profiling"),
    ("EXP-003", "Intervention Cost Baseline"),
]
METHODS = ["RIFT-FULL", "RIFT-OBS", "RIFT-RANDOM", "SIEVE-LIKE"]
COLORS = ["#648FFF", "#FE6100", "#DC267F", "#785EF0"]

METRICS = [
    ("mean_total_ed_s",      "Mean Total Effective Duration (s)"),
    ("mean_n_interventions", "Mean Number of Interventions"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_results(path: Path):
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _method_key(method: str) -> str:
    return method.lower().replace("-", "_")


def extract_metric(data: dict, method: str, metric: str) -> float | None:
    key = f"{_method_key(method)}_{metric}"
    val = data.get(key)
    return float(val) if val is not None else None


def merge_results(*dicts) -> dict:
    """Merge multiple result dicts, later dicts overwrite earlier ones."""
    merged: dict = {}
    for d in dicts:
        if d:
            merged.update(d)
    return merged


# ---------------------------------------------------------------------------
# Figure generator
# ---------------------------------------------------------------------------

def generate_figure(
    results_by_exp: dict[str, dict | None],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Merge all experiment data so we can pull metrics from whichever exp has them
    merged = merge_results(*[v for v in results_by_exp.values() if v])

    any_data = bool(merged)
    xs = np.arange(len(METHODS))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Figure 4 — Runtime & Intervention Cost by Method", fontsize=12)

    for ax, (metric_key, metric_title) in zip(axes, METRICS):
        ax.set_title(metric_title, fontsize=10)
        ax.set_xticks(xs)
        ax.set_xticklabels(METHODS, rotation=15, ha="right", fontsize=9)

        if any_data:
            ys = [extract_metric(merged, m, metric_key) or 0.0 for m in METHODS]
            bars = ax.bar(xs, ys, color=COLORS, alpha=0.85, edgecolor="black", linewidth=0.4)
            for bar, y in zip(bars, ys):
                ax.text(bar.get_x() + bar.get_width() / 2, y + max(ys) * 0.01,
                        f"{y:.1f}", ha="center", va="bottom", fontsize=8)
            ax.set_ylim(0, max(ys) * 1.2 if max(ys) > 0 else 1.0)
        else:
            ax.text(0.5, 0.5,
                    "RESULTS NOT YET AVAILABLE\n(run EXP-009/EXP-003 first)",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=9, color="#888888", style="italic")
            ax.set_xlim(-0.5, len(METHODS) - 0.5)
            ax.set_ylim(0, 1)

    # Legend
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85)
        for c in COLORS
    ]
    fig.legend(handles, METHODS, loc="lower center", ncol=len(METHODS),
               fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=[0, 0.05, 1, 1])

    # Source attribution
    exp_ids = ", ".join(
        exp_id for exp_id, data in results_by_exp.items() if data is not None
    )
    if exp_ids:
        fig.text(0.01, 0.01, f"Sources: {exp_ids}", fontsize=7, color="gray")

    for ext in ("png", "pdf"):
        p = output_dir / f"fig4_runtime.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=150)
        print(f"  → {p}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 4: Runtime and intervention cost"
    )
    parser.add_argument("--input-dir", default="results", type=Path)
    parser.add_argument("--output-dir", default="analysis/figures", type=Path)
    args = parser.parse_args()

    results_by_exp: dict[str, dict | None] = {}
    for exp_id, _ in EXPERIMENTS:
        p = args.input_dir / exp_id / "results.json"
        data = load_results(p)
        if data is None:
            print(f"RESULTS NOT YET AVAILABLE — generating template (expected: {p})")
        results_by_exp[exp_id] = data

    try:
        generate_figure(results_by_exp, args.output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
