#!/usr/bin/env python3
"""Table 1 — Main Results Table (LaTeX + CSV).

Input:  results/EXP-001/results.json  (optional)
Output: analysis/tables/table1_main_results.tex
        analysis/tables/table1_main_results.csv

Columns: Method | Precision@1 | Detection Latency | Abstention Rate
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
METHODS = [
    ("RIFT-FULL",   "RIFT-FULL"),
    ("RIFT-OBS",    "RIFT-OBS"),
    ("RIFT-RANDOM", "RIFT-RANDOM"),
    ("SIEVE-LIKE",  "SIEVE-LIKE"),
    ("ORACLE",      "ORACLE\\textsuperscript{†}"),
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


def _key(method: str) -> str:
    return method.lower().replace("-", "_")


def _fmt(v: Any) -> str:
    if v is None:
        return "---"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _latex_escape(s: str) -> str:
    # Only escape characters not already intentionally LaTeX
    if "\\" in s or "{" in s:
        return s
    return s.replace("_", "\\_").replace("%", "\\%").replace("&", "\\&")


def build_rows(data: dict | None) -> list[dict]:
    rows = []
    for method_key, method_display in METHODS:
        k = _key(method_key)
        if data is not None:
            row = {
                "Method":             method_display,
                "Precision@1":        _fmt(data.get(f"{k}_raw_p1")),
                "Cond. P@1":          _fmt(data.get(f"{k}_cond_p1")),
                "Detection Latency":  _fmt(data.get(f"{k}_mean_latency_s")),
                "Abstention Rate":    _fmt(data.get(f"{k}_abstention_rate")),
            }
        else:
            row = {
                "Method":             method_display,
                "Precision@1":        "PENDING",
                "Cond. P@1":          "PENDING",
                "Detection Latency":  "PENDING",
                "Abstention Rate":    "PENDING",
            }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use plain method names (strip LaTeX markup) for CSV
    plain_rows = [{k: v.replace("\\textsuperscript{†}", "†")
                     .replace("\\", "").replace("{", "").replace("}", "")
                   for k, v in row.items()}
                  for row in rows]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(plain_rows[0].keys()))
        writer.writeheader()
        writer.writerows(plain_rows)
    print(f"  → {path}")


def write_latex(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    col_spec = "l" + "r" * (len(cols) - 1)
    header = " & ".join(_latex_escape(c) for c in cols)
    lines = [
        "% Table 1 — Main Results",
        "% AUTO-GENERATED — do not edit by hand",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Main results: Precision@1, Detection Latency, and Abstention Rate "
        "per method on the development split. "
        "\\textsuperscript{†}ORACLE UPPER BOUND --- not a deployable method.}",
        "  \\label{tab:main_results}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\hline",
        f"    {header} \\\\",
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
        description="Generate Table 1: Main results (LaTeX + CSV)"
    )
    parser.add_argument("--input-dir", default="results", type=Path)
    parser.add_argument("--output-dir", default="analysis/tables", type=Path)
    args = parser.parse_args()

    results_path = args.input_dir / "EXP-001" / "results.json"
    data = load_results(results_path)
    if data is None:
        print("RESULTS NOT YET AVAILABLE — generating template "
              f"(expected: {results_path})")

    try:
        rows = build_rows(data)
        write_csv(rows, args.output_dir / "table1_main_results.csv")
        write_latex(rows, args.output_dir / "table1_main_results.tex")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
