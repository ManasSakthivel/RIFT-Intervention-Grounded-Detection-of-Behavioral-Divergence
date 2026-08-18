#!/usr/bin/env python3
"""RIFT Table Generators — Phase 4.5

Reproducible scripts that generate paper tables from experiment artifacts.
No hardcoded final numbers — all values loaded from results/ or analysis/.

Tables generated:
  table_main_results.{csv,json,tex}    — Main P@1 comparison (H1–H2)
  table_ablation.{csv,json,tex}        — Ablation results
  table_cost.{csv,json,tex}            — Intervention cost comparison (H4)
  table_statistics.{csv,json,tex}      — Hypothesis test results (p-values, Cliff's δ)
  table_scenario_coverage.{csv,json}   — Scenario type breakdown

Usage:
    python analysis/tables/generate_tables.py [--results-dir results/]
        [--analysis-dir analysis/] [--output-dir analysis/tables/]

Status: IMPLEMENTED / MAC_TESTED (produces empty/placeholder tables when no data)
"""
from __future__ import annotations

import argparse
import csv
import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> Optional[Dict[str, Any]]:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("# No data — run experiments first\n")
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {path}")


def _write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  → {path}")


def _write_latex(rows: List[Dict[str, Any]], path: Path, caption: str = "") -> None:
    """Write a simple LaTeX tabular environment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(f"% No data — run experiments first\n% {caption}\n")
        return

    cols = list(rows[0].keys())
    col_spec = "l" + "r" * (len(cols) - 1)

    lines = [
        "\\begin{table}[t]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\hline",
        "    " + " & ".join(str(c).replace("_", "\\_") for c in cols) + " \\\\",
        "    \\hline",
    ]
    for row in rows:
        line = "    " + " & ".join(
            f"{v:.3f}" if isinstance(v, float) else str(v).replace("_", "\\_")
            for v in row.values()
        ) + " \\\\"
        lines.append(line)
    lines += [
        "    \\hline",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    path.write_text("\n".join(lines) + "\n")
    print(f"  → {path}")


# ---------------------------------------------------------------------------
# Table 1: Main results
# ---------------------------------------------------------------------------

def table_main_results(
    results_dir: Path,
    output_dir: Path,
) -> None:
    """Main P@1 comparison table across all methods."""
    data = _load(results_dir / "EXP-001" / "metrics.json")

    methods = ["RIFT-FULL", "RIFT-OBS", "RIFT-RANDOM", "SIEVE-LIKE", "ORACLE-UPPER-BOUND†"]
    rows = []

    if data and data.get("status") not in ("PENDING_LINUX", "DRY_RUN"):
        for m in methods:
            key = m.lower().replace("†", "").replace("-", "_")
            rows.append({
                "Method": m,
                "Raw P@1": data.get(f"{key}_raw_p1", "—"),
                "Cond. P@1": data.get(f"{key}_cond_p1", "—"),
                "Coverage": data.get(f"{key}_coverage", "—"),
                "Abstention": data.get(f"{key}_abstention_rate", "—"),
                "Latency (s)": data.get(f"{key}_mean_latency_s", "—"),
            })
    else:
        for m in methods:
            rows.append({
                "Method": m,
                "Raw P@1": "PENDING",
                "Cond. P@1": "PENDING",
                "Coverage": "PENDING",
                "Abstention": "PENDING",
                "Latency (s)": "PENDING",
            })

    _write_csv(rows, output_dir / "table_main_results.csv")
    _write_json(rows, output_dir / "table_main_results.json")
    _write_latex(rows, output_dir / "table_main_results.tex",
                 caption="Main results: Precision@1 by method on development set. "
                 "†ORACLE UPPER BOUND — not a deployable method.")


# ---------------------------------------------------------------------------
# Table 2: Ablation results
# ---------------------------------------------------------------------------

def table_ablation(
    results_dir: Path,
    output_dir: Path,
) -> None:
    """Ablation study table."""
    ablations = [
        ("RIFT-FULL", "EXP-001"),
        ("RIFT-OBS (no intervention)", "EXP-005"),
        ("RIFT-RANDOM (no MSIS)", "EXP-006"),
        ("RIFT-ONE-SHOT (no closed-loop)", "EXP-013"),
    ]
    rows = []
    for label, exp_id in ablations:
        data = _load(results_dir / exp_id / "metrics.json")
        if data and data.get("status") not in ("PENDING_LINUX", "DRY_RUN"):
            rows.append({
                "Ablation": label,
                "Raw P@1": data.get("raw_p1", "—"),
                "Cond. P@1": data.get("cond_p1", "—"),
                "Wilcoxon p": data.get("wilcoxon_p", "—"),
                "Cliff's δ": data.get("cliffs_delta", "—"),
            })
        else:
            rows.append({
                "Ablation": label,
                "Raw P@1": "PENDING",
                "Cond. P@1": "PENDING",
                "Wilcoxon p": "PENDING",
                "Cliff's δ": "PENDING",
            })

    _write_csv(rows, output_dir / "table_ablation.csv")
    _write_json(rows, output_dir / "table_ablation.json")
    _write_latex(rows, output_dir / "table_ablation.tex",
                 caption="Ablation study: effect of removing RIFT components.")


# ---------------------------------------------------------------------------
# Table 3: Intervention cost
# ---------------------------------------------------------------------------

def table_cost(
    results_dir: Path,
    output_dir: Path,
) -> None:
    """Intervention cost table (H4)."""
    pairs = [
        ("RIFT-FULL", "EXP-014"),
        ("RIFT-RANDOM", "EXP-014"),
    ]
    rows = []
    for label, exp_id in pairs:
        data = _load(results_dir / exp_id / "metrics.json")
        key = label.lower().replace("-", "_")
        if data and data.get("status") not in ("PENDING_LINUX", "DRY_RUN"):
            rows.append({
                "Method": label,
                "Mean total_ed_s": data.get(f"{key}_mean_ed_s", "—"),
                "Mean n_interventions": data.get(f"{key}_mean_n_interventions", "—"),
                "P@1 (TOST equiv.)": data.get(f"{key}_p1", "—"),
            })
        else:
            rows.append({
                "Method": label,
                "Mean total_ed_s": "PENDING",
                "Mean n_interventions": "PENDING",
                "P@1 (TOST equiv.)": "PENDING",
            })

    _write_csv(rows, output_dir / "table_cost.csv")
    _write_json(rows, output_dir / "table_cost.json")
    _write_latex(rows, output_dir / "table_cost.tex",
                 caption="Intervention cost comparison (H4).")


# ---------------------------------------------------------------------------
# Table 4: Hypothesis test statistics
# ---------------------------------------------------------------------------

def table_statistics(
    analysis_dir: Path,
    output_dir: Path,
) -> None:
    """Hypothesis test statistics table."""
    stats_file = analysis_dir / "statistics" / "confirmatory_tests.json"
    data = _load(stats_file)

    hypotheses = ["H1", "H2", "H3", "H4_acc", "H4_cost", "H5"]
    rows = []

    if data and "tests" in data:
        tests = data["tests"]
        for h in hypotheses:
            t = tests.get(h, {})
            rows.append({
                "Hypothesis": h,
                "Test": t.get("test_name", "—")[:30],
                "Statistic": t.get("statistic", "—"),
                "p-value (corrected)": t.get("pvalue", "—"),
                "Cliff's δ": t.get("cliffs_delta", "—"),
                "CI lower": t.get("cliffs_delta_ci", ["—", "—"])[0],
                "CI upper": t.get("cliffs_delta_ci", ["—", "—"])[1],
                "Effect size": t.get("effect_size", "—"),
                "Significant": t.get("significant", "—"),
            })
    else:
        for h in hypotheses:
            rows.append({
                "Hypothesis": h,
                "Test": "PENDING",
                "Statistic": "PENDING",
                "p-value (corrected)": "PENDING",
                "Cliff's δ": "PENDING",
                "CI lower": "PENDING",
                "CI upper": "PENDING",
                "Effect size": "PENDING",
                "Significant": "PENDING",
            })

    _write_csv(rows, output_dir / "table_statistics.csv")
    _write_json(rows, output_dir / "table_statistics.json")
    _write_latex(rows, output_dir / "table_statistics.tex",
                 caption="Confirmatory hypothesis test results with Holm-Bonferroni correction.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RIFT paper tables")
    parser.add_argument("--results-dir", "-r", default="results", type=Path)
    parser.add_argument("--analysis-dir", "-a", default="analysis", type=Path)
    parser.add_argument("--output-dir", "-o", default="analysis/tables", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n==> Generating RIFT tables → {output_dir}/")
    table_main_results(args.results_dir, output_dir)
    table_ablation(args.results_dir, output_dir)
    table_cost(args.results_dir, output_dir)
    table_statistics(args.analysis_dir, output_dir)
    print("==> Done.")


if __name__ == "__main__":
    main()
