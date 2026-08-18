#!/usr/bin/env python3
"""Table 3 — Statistical Test Results (LaTeX + CSV).

Input:  results/statistical_tests.json  (or results/EXP-*/statistics.json)
Output: analysis/tables/table3_statistics.tex
        analysis/tables/table3_statistics.csv

Columns: Hypothesis | Test | p-value | Cliff's delta | Corrected-alpha | Significant
Reads all values from result artifacts. Never fabricates numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Six confirmatory hypotheses per pre-registration
HYPOTHESES = ["H1", "H2", "H3", "H4_acc", "H4_cost", "H5"]

# Holm-Bonferroni corrected alpha boundaries (6 tests, alpha=0.05)
# Ordered by rank: alpha / (6, 5, 4, 3, 2, 1)
HOLM_ALPHAS = {
    "H1":     round(0.05 / 6, 5),
    "H2":     round(0.05 / 5, 5),
    "H3":     round(0.05 / 4, 5),
    "H4_acc": round(0.05 / 3, 5),
    "H4_cost": round(0.05 / 2, 5),
    "H5":     round(0.05 / 1, 5),
}

# Candidate paths for statistics results
STATS_SEARCH_PATHS = [
    "statistical_tests.json",
    "statistics/confirmatory_tests.json",
    "EXP-001/statistics.json",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_stats(input_dir: Path):
    """Try known locations for the statistical tests JSON."""
    for rel in STATS_SEARCH_PATHS:
        p = input_dir / rel
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _fmt_p(v: Any) -> str:
    if v is None:
        return "---"
    try:
        fv = float(v)
        if fv < 0.001:
            return "< 0.001"
        return f"{fv:.4f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_delta(v: Any) -> str:
    if v is None:
        return "---"
    try:
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return str(v)


def build_rows(data: dict | None) -> list[dict]:
    rows = []
    tests = data.get("tests", {}) if data else {}
    for h in HYPOTHESES:
        t = tests.get(h, {})
        corrected_alpha = HOLM_ALPHAS.get(h, "---")
        if t:
            pval = t.get("pvalue") or t.get("p_value") or t.get("corrected_pvalue")
            delta = t.get("cliffs_delta")
            ci = t.get("cliffs_delta_ci", [None, None])
            sig = t.get("significant")
            row = {
                "Hypothesis":       h,
                "Test":             str(t.get("test_name", "---"))[:35],
                "p-value":          _fmt_p(pval),
                "Cliff's delta":    _fmt_delta(delta),
                "CI [low, high]":   (
                    f"[{_fmt_delta(ci[0])}, {_fmt_delta(ci[1])}]"
                    if ci[0] is not None else "---"
                ),
                "Corrected alpha":  str(corrected_alpha),
                "Significant":      ("Yes" if sig else "No") if sig is not None else "---",
            }
        else:
            row = {
                "Hypothesis":      h,
                "Test":            "PENDING",
                "p-value":         "PENDING",
                "Cliff's delta":   "PENDING",
                "CI [low, high]":  "PENDING",
                "Corrected alpha": str(corrected_alpha),
                "Significant":     "PENDING",
            }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {path}")


def write_latex(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    col_spec = "l" + "c" * (len(cols) - 1)
    header_tex = " & ".join(
        c.replace("'", "'").replace("[", "{[").replace("]", "]}") for c in cols
    )
    lines = [
        "% Table 3 — Statistical Test Results",
        "% AUTO-GENERATED — do not edit by hand",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Confirmatory hypothesis test results. "
        "p-values are reported after Holm-Bonferroni correction. "
        "Cliff's $\\delta$ effect sizes with 95\\% bootstrap CI. "
        "$^*$Significant at corrected $\\alpha$.}",
        "  \\label{tab:statistics}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\hline",
        f"    {header_tex} \\\\",
        "    \\hline",
    ]
    for row in rows:
        cells = " & ".join(str(v) for v in row.values())
        lines.append(f"    {cells} \\\\")
    lines += [
        "    \\hline",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    path.write_text("\n".join(lines) + "\n")
    print(f"  → {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Table 3: Statistical test results (LaTeX + CSV)"
    )
    parser.add_argument("--input-dir", default="results", type=Path,
                        help="Directory containing statistical test JSON artifacts")
    parser.add_argument("--output-dir", default="analysis/tables", type=Path)
    args = parser.parse_args()

    data = load_stats(args.input_dir)
    if data is None:
        print("RESULTS NOT YET AVAILABLE — generating template "
              f"(searched: {[str(args.input_dir / r) for r in STATS_SEARCH_PATHS]})")

    try:
        rows = build_rows(data)
        write_csv(rows, args.output_dir / "table3_statistics.csv")
        write_latex(rows, args.output_dir / "table3_statistics.tex")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
