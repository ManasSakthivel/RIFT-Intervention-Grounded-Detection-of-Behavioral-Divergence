#!/usr/bin/env python3
"""Figure 2 — Baseline Comparison (Development Set).

Input:  results/EXP-001/results.json
        results/EXP-005/results.json
        results/EXP-007/results.json
Output: analysis/figures/fig2_baseline_comparison.png
        analysis/figures/fig2_baseline_comparison.pdf

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
EXPERIMENTS = [
    ("EXP-001", "Primary (full pipeline)"),
    ("EXP-005", "RIFT-OBS (no intervention)"),
    ("EXP-007", "Confounded dev set"),
]
METHODS = ["RIFT-FULL", "RIFT-OBS", "RIFT-RANDOM", "SIEVE-LIKE", "ORACLE"]
COLORS = ["#648FFF", "#FE6100", "#DC267F", "#785EF0", "#FFB000"]


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
    return method.lower().replace("-", "_").replace("†", "")


def extract_metric(data: dict, method: str, metric: str = "raw_p1") -> float | None:
    k = _method_key(method)
    val = data.get(f"{k}_{metric}")
    return float(val) if val is not None else None


# ---------------------------------------------------------------------------
# Figure generator
# ---------------------------------------------------------------------------

def generate_figure(results_by_exp: dict[str, dict | None], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    any_data = any(v is not None for v in results_by_exp.values())

    fig, axes = plt.subplots(1, len(EXPERIMENTS), figsize=(14, 4.5), sharey=True)
    fig.suptitle("Figure 2 — Baseline Comparison: Precision@1 Across Experiment Sets",
                 fontsize=12, y=1.01)

    xs = np.arange(len(METHODS))
    for ax, (exp_id, label) in zip(axes, EXPERIMENTS):
        ax.set_title(f"{exp_id}\n{label}", fontsize=9)
        ax.set_ylim(0, 1.05)
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_xticks(xs)
        ax.set_xticklabels(
            [m.replace("ORACLE", "ORACLE†") for m in METHODS],
            rotation=25, ha="right", fontsize=7,
        )
        data = results_by_exp.get(exp_id)
        if data is not None and any_data:
            ys = [extract_metric(data, m, "raw_p1") or 0.0 for m in METHODS]
            ax.bar(xs, ys, color=COLORS, alpha=0.85, edgecolor="black", linewidth=0.4)
            for xi, yi in zip(xs, ys):
                ax.text(xi, yi + 0.01, f"{yi:.2f}", ha="center", va="bottom", fontsize=7)
        else:
            ax.text(0.5, 0.5,
                    f"RESULTS NOT YET AVAILABLE\n({exp_id})",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=8, color="#888888", style="italic")

    if len(axes) > 0:
        axes[0].set_ylabel("Precision@1", fontsize=10)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85)
        for c in COLORS
    ]
    fig.legend(handles, METHODS, loc="lower center", ncol=len(METHODS),
               fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.text(0.99, 0.01, "†ORACLE UPPER BOUND — not deployable",
             ha="right", fontsize=7, color="gray", style="italic")
    fig.tight_layout()

    for ext in ("png", "pdf"):
        p = output_dir / f"fig2_baseline_comparison.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=150)
        print(f"  → {p}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 2: Baseline comparison across experiment sets"
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
