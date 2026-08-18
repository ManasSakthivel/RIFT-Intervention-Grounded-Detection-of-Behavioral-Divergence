#!/usr/bin/env python3
"""Table 2 — Ablation Table (LaTeX + CSV).

Input:  results/EXP-005/results.json  (RIFT-OBS: no intervention)
        results/EXP-006/results.json  (RIFT-RANDOM: no MSIS)
        results/EXP-013/results.json  (RIFT-ONE-SHOT: no closed-loop)
Output: analysis/tables/table2_ablation.tex
        analysis/tables/table2_ablation.csv

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
ABLATIONS = [
    ("EXP-001", "RIFT-FULL",     "Full system (all components)"),
    ("EXP-005", "RIFT-OBS",      "No active intervention"),
    ("EXP-006", "RIFT-RANDOM",   "No MSIS (random selection)"),
    ("EXP-013", "RIFT-ONE-SHOT", "No closed-loop (single pass)"),
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


def _fmt(v: Any) -> str:
    if v is None:
        return "---"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def build_rows(results_by_exp: dict[str, dict | None]) -> list[dict]:
    rows = []
    for exp_id, method_key, description in ABLATIONS:
        data = results_by_exp.get(exp_id)
        if data is not None:
            row = {
                "Ablation":      method_key,
                "Description":   description,
                "Raw P@1":       _fmt(data.get("raw_p1")),
                "Cond. P@1":     _fmt(data.get("cond_p1")),
                "Wilcoxon p":    _fmt(data.get("wilcoxon_p")),
                "Cliff's delta": _fmt(data.get("cliffs_delta")),
                "Significant":   str(data.get("significant", "---")),
            }
        else:
            row = {
                "Ablation":      method_key,
                "Description":   description,
                "Raw P@1":       "PENDING",
                "Cond. P@1":     "PENDING",
                "Wilcoxon p":    "PENDING",
                "Cliff's delta": "PENDING",
                "Significant":   "PENDING",
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
    # Omit 'Description' column from LaTeX (put in caption)
    tex_keys = [k for k in rows[0].keys() if k != "Description"]
    col_spec = "l" + "r" * (len(tex_keys) - 1)
    header_tex = " & ".join(k.replace("'", "'").replace("@", "@") for k in tex_keys)

    lines = [
        "% Table 2 — Ablation Study",
        "% AUTO-GENERATED — do not edit by hand",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Ablation study: effect of removing RIFT components. "
        "RIFT-OBS removes active intervention; RIFT-RANDOM removes MSIS selection; "
        "RIFT-ONE-SHOT removes the closed-loop update step.}",
        "  \\label{tab:ablation}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\hline",
        f"    {header_tex} \\\\",
        "    \\hline",
    ]
    for row in rows:
        cells = " & ".join(str(row[k]) for k in tex_keys)
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
        description="Generate Table 2: Ablation study (LaTeX + CSV)"
    )
    parser.add_argument("--input-dir", default="results", type=Path)
    parser.add_argument("--output-dir", default="analysis/tables", type=Path)
    args = parser.parse_args()

    results_by_exp: dict[str, dict | None] = {}
    for exp_id, _, _ in ABLATIONS:
        p = args.input_dir / exp_id / "results.json"
        data = load_results(p)
        if data is None:
            print(f"RESULTS NOT YET AVAILABLE — generating template (expected: {p})")
        results_by_exp[exp_id] = data

    try:
        rows = build_rows(results_by_exp)
        write_csv(rows, args.output_dir / "table2_ablation.csv")
        write_latex(rows, args.output_dir / "table2_ablation.tex")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
