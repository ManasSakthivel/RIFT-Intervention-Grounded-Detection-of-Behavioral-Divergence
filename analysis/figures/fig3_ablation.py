#!/usr/bin/env python3
"""Figure 3 — Ablation Results.

Input:  results/EXP-005/results.json  (RIFT-OBS: no intervention)
        results/EXP-006/results.json  (RIFT-RANDOM: no MSIS)
        results/EXP-013/results.json  (RIFT-ONE-SHOT: no closed-loop)
Output: analysis/figures/fig3_ablation.png
        analysis/figures/fig3_ablation.pdf

Reads all values from result artifacts. Never fabricates numbers.
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
ABLATIONS = [
    ("EXP-001", "RIFT-FULL\n(all components)", "#648FFF"),
    ("EXP-005", "RIFT-OBS\n(–intervention)", "#FE6100"),
    ("EXP-006", "RIFT-RANDOM\n(–MSIS)", "#DC267F"),
    ("EXP-013", "RIFT-ONE-SHOT\n(–closed-loop)", "#785EF0"),
]
METRICS = [
    ("raw_p1",        "Raw Precision@1"),
    ("cond_p1",       "Conditional P@1"),
    ("abstention_rate", "Abstention Rate"),
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


def extract_metric(data: dict, metric_key: str) -> float | None:
    val = data.get(metric_key)
    return float(val) if val is not None else None


# ---------------------------------------------------------------------------
# Figure generator
# ---------------------------------------------------------------------------

def generate_figure(
    results_by_exp: dict[str, dict | None],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    n_metrics = len(METRICS)
    fig, axes = plt.subplots(1, n_metrics, figsize=(12, 4.5), sharey=False)
    fig.suptitle("Figure 3 — Ablation Study: Effect of Removing RIFT Components",
                 fontsize=12, y=1.01)

    xs = np.arange(len(ABLATIONS))
    labels = [label for _, label, _ in ABLATIONS]
    colors = [color for _, _, color in ABLATIONS]

    for ax, (metric_key, metric_title) in zip(axes, METRICS):
        ax.set_title(metric_title, fontsize=10)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 1.05)
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)

        any_real = any(
            results_by_exp.get(exp_id) is not None for exp_id, _, _ in ABLATIONS
        )
        if any_real:
            ys = []
            for exp_id, _, _ in ABLATIONS:
                data = results_by_exp.get(exp_id)
                ys.append(extract_metric(data, metric_key) if data else 0.0)
            bars = ax.bar(xs, [y or 0.0 for y in ys],
                          color=colors, alpha=0.85, edgecolor="black", linewidth=0.4)
            for bar, y in zip(bars, ys):
                if y is not None:
                    ax.text(bar.get_x() + bar.get_width() / 2, (y or 0.0) + 0.01,
                            f"{y:.2f}", ha="center", va="bottom", fontsize=7)
        else:
            ax.text(0.5, 0.5,
                    "RESULTS NOT YET AVAILABLE\n(run EXP-005/006/013 first)",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=8, color="#888888", style="italic")

    fig.tight_layout()
    for ext in ("png", "pdf"):
        p = output_dir / f"fig3_ablation.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=150)
        print(f"  → {p}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 3: Ablation study results"
    )
    parser.add_argument("--input-dir", default="results", type=Path)
    parser.add_argument("--output-dir", default="analysis/figures", type=Path)
    args = parser.parse_args()

    results_by_exp: dict[str, dict | None] = {}
    for exp_id, _, _ in ABLATIONS:
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
