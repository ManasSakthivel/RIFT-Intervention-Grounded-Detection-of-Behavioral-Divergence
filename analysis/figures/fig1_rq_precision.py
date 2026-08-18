#!/usr/bin/env python3
"""Figure 1 — Main RQ Results: Precision@1 comparison bar chart.

Input:  results/EXP-001/results.json  (optional)
Output: analysis/figures/fig1_rq_precision.png
        analysis/figures/fig1_rq_precision.pdf
        analysis/figures/fig1_rq_precision.csv

Reads all values from results artifacts. Never fabricates numbers.
Produces a labelled placeholder when results are not yet available.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
METHODS = ["RIFT-FULL", "RIFT-OBS", "RIFT-RANDOM", "SIEVE-LIKE", "ORACLE"]
COLORS = {
    "RIFT-FULL":   "#648FFF",
    "RIFT-OBS":    "#FE6100",
    "RIFT-RANDOM": "#DC267F",
    "SIEVE-LIKE":  "#785EF0",
    "ORACLE":      "#FFB000",
}
DEFAULT_COLOR = "#808080"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_results(path: Path):
    """Return parsed JSON dict, or None if the file is missing/unreadable."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _method_key(method: str) -> str:
    return method.lower().replace("-", "_").replace("†", "")


def extract_precision(data: dict) -> dict[str, float | None]:
    """Pull Precision@1 values keyed by method name."""
    out: dict[str, float | None] = {}
    for m in METHODS:
        k = _method_key(m)
        val = data.get(f"{k}_raw_p1") or data.get(f"precision_at_1_{k}")
        out[m] = float(val) if val is not None else None
    return out


# ---------------------------------------------------------------------------
# Figure generator
# ---------------------------------------------------------------------------

def generate_figure(results, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    is_template = results is None or not any(
        results.get(f"{_method_key(m)}_raw_p1") is not None for m in METHODS
    )

    precision: dict[str, float | None] = {}
    if is_template:
        precision = {m: None for m in METHODS}
    else:
        precision = extract_precision(results)

    # --- CSV output ---
    csv_path = output_dir / "fig1_rq_precision.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "precision_at_1"])
        writer.writeheader()
        for m in METHODS:
            writer.writerow({"method": m, "precision_at_1": precision.get(m, "PENDING")})
    print(f"  → {csv_path}")

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_title("Figure 1 — Precision@1 by Method (dev split)", fontsize=12, pad=10)
    ax.set_ylabel("Precision@1", fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6, label="Chance (0.5)")

    xs = list(range(len(METHODS)))
    if is_template:
        ax.text(0.5, 0.5,
                "RESULTS NOT YET AVAILABLE — generating template\n(run EXP-001 first)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="#888888", style="italic")
        ax.set_xticks(xs)
        ax.set_xticklabels(METHODS, rotation=20, ha="right", fontsize=8)
    else:
        ys = [precision.get(m) or 0.0 for m in METHODS]
        cs = [COLORS.get(m, DEFAULT_COLOR) for m in METHODS]
        bars = ax.bar(xs, ys, color=cs, alpha=0.85, edgecolor="black", linewidth=0.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(
            [m.replace("ORACLE", "ORACLE†") for m in METHODS],
            rotation=20, ha="right", fontsize=8,
        )
        for bar, val in zip(bars, ys):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                    f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    ax.legend(fontsize=8)
    fig.text(0.95, 0.01, "†ORACLE UPPER BOUND — not deployable",
             ha="right", fontsize=7, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])

    for ext in ("png", "pdf"):
        p = output_dir / f"fig1_rq_precision.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=150)
        print(f"  → {p}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Figure 1: Precision@1 bar chart")
    parser.add_argument("--input-dir", default="results", type=Path,
                        help="Directory containing experiment result subdirectories")
    parser.add_argument("--output-dir", default="analysis/figures", type=Path,
                        help="Directory to write output files")
    args = parser.parse_args()

    results_path = args.input_dir / "EXP-001" / "results.json"
    results = load_results(results_path)
    if results is None:
        print("RESULTS NOT YET AVAILABLE — generating template "
              f"(expected: {results_path})")

    try:
        generate_figure(results, args.output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
