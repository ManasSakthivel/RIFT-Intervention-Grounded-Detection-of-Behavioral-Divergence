#!/usr/bin/env python3
"""Table 4 — Scenario / Robustness Summary (LaTeX + CSV).

Input:  datasets/rift_faults/manifest.json
        datasets/rift_faults/development.json  (for per-type counts)
Output: analysis/tables/table4_scenarios.tex
        analysis/tables/table4_scenarios.csv

Content: Fault type | Count | Confounded | Split breakdown | Notes
Reads all values from dataset manifest/schema. Never fabricates numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASET_DIR_DEFAULT = "datasets/rift_faults"
MANIFEST_FILE = "manifest.json"
SPLIT_FILES = {
    "DEVELOPMENT": "development.json",
    "VALIDATION": "validation.json",
    "HELD_OUT_TEST": "held_out_test.json",
}
FAULT_TYPE_LABELS = {
    "NETWORK_LATENCY":     "Network Latency",
    "PACKET_LOSS":         "Packet Loss",
    "SERVICE_DEGRADATION": "Service Degradation",
    "RESOURCE_CONTENTION": "Resource Contention",
    "QUEUEING":            "Queueing",
    "DEPENDENCY_FAILURE":  "Dependency Failure",
    "MULTI_CAUSE":         "Multi-cause",
    "CONFOUNDED":          "Confounded (all types)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def count_scenarios_by_type(dataset_dir: Path) -> dict[str, dict]:
    """
    Returns a dict keyed by fault_type, with per-split counts and confounded flag.
    Falls back to manifest.json if split files are absent.
    """
    type_stats: dict[str, dict] = {}

    for split_name, filename in SPLIT_FILES.items():
        split_data = load_json(dataset_dir / filename)
        if split_data is None:
            continue
        scenarios = split_data.get("scenarios", [])
        for sc in scenarios:
            ft = sc.get("fault_type", "UNKNOWN")
            confounded = sc.get("confounded", False)
            if ft not in type_stats:
                type_stats[ft] = {
                    "total": 0,
                    "confounded": 0,
                    "DEVELOPMENT": 0,
                    "VALIDATION": 0,
                    "HELD_OUT_TEST": 0,
                }
            type_stats[ft]["total"] += 1
            if confounded:
                type_stats[ft]["confounded"] += 1
            type_stats[ft][split_name] = type_stats[ft].get(split_name, 0) + 1

    return type_stats


def build_rows_from_split_data(
    type_stats: dict[str, dict],
    manifest: dict | None,
) -> list[dict]:
    rows = []
    # Maintain canonical ordering from manifest if possible
    ordered_types = list(FAULT_TYPE_LABELS.keys())
    seen = set()

    for ft in ordered_types + sorted(set(type_stats.keys()) - set(ordered_types)):
        if ft in seen:
            continue
        seen.add(ft)
        label = FAULT_TYPE_LABELS.get(ft, ft)
        stats = type_stats.get(ft, {})
        rows.append({
            "Fault Type":    label,
            "Total":         stats.get("total", 0),
            "Confounded":    stats.get("confounded", 0),
            "Dev Split":     stats.get("DEVELOPMENT", 0),
            "Val Split":     stats.get("VALIDATION", 0),
            "Test Split":    stats.get("HELD_OUT_TEST", 0),
        })

    # Summary row
    totals = {
        "Fault Type": "TOTAL",
        "Total":      sum(r["Total"] for r in rows),
        "Confounded": sum(r["Confounded"] for r in rows),
        "Dev Split":  sum(r["Dev Split"] for r in rows),
        "Val Split":  sum(r["Val Split"] for r in rows),
        "Test Split": sum(r["Test Split"] for r in rows),
    }
    rows.append(totals)
    return rows


def build_rows_from_manifest(manifest: dict) -> list[dict]:
    """Fallback: build summary rows purely from manifest (no per-type split info)."""
    by_fault = manifest.get("by_fault_type", {})
    splits = manifest.get("split_counts", {})
    rows = []
    for ft, count in by_fault.items():
        label = FAULT_TYPE_LABELS.get(ft, ft)
        rows.append({
            "Fault Type": label,
            "Total":      count,
            "Confounded": count if ft == "CONFOUNDED" else 0,
            "Dev Split":  "---",
            "Val Split":  "---",
            "Test Split": "---",
        })
    rows.append({
        "Fault Type": "TOTAL",
        "Total":      manifest.get("total_scenarios", "---"),
        "Confounded": manifest.get("confounded", "---"),
        "Dev Split":  splits.get("DEVELOPMENT", "---"),
        "Val Split":  splits.get("VALIDATION", "---"),
        "Test Split": splits.get("HELD_OUT_TEST", "---"),
    })
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
    col_spec = "l" + "r" * (len(cols) - 1)
    header_tex = " & ".join(c for c in cols)
    lines = [
        "% Table 4 — Scenario / Robustness Summary",
        "% AUTO-GENERATED — do not edit by hand",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Benchmark scenario composition by fault type and dataset split. "
        "\\emph{Confounded} scenarios contain simultaneous independent faults "
        "that challenge attribution.}",
        "  \\label{tab:scenarios}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\hline",
        f"    {header_tex} \\\\",
        "    \\hline",
    ]
    for i, row in enumerate(rows):
        # Bold the TOTAL row (last)
        if row.get("Fault Type") == "TOTAL":
            cells = " & ".join(f"\\textbf{{{v}}}" for v in row.values())
        else:
            cells = " & ".join(str(v) for v in row.values())
        lines.append(f"    {cells} \\\\")
        if row.get("Fault Type") == "TOTAL":
            lines.append("    \\hline")
    if rows and rows[-1].get("Fault Type") != "TOTAL":
        lines.append("    \\hline")
    lines += [
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
        description="Generate Table 4: Scenario/robustness summary (LaTeX + CSV)"
    )
    parser.add_argument("--input-dir", default=DATASET_DIR_DEFAULT, type=Path,
                        help="Directory containing rift_faults dataset files")
    parser.add_argument("--output-dir", default="analysis/tables", type=Path)
    args = parser.parse_args()

    manifest = load_json(args.input_dir / MANIFEST_FILE)
    if manifest is None:
        print("RESULTS NOT YET AVAILABLE — generating template "
              f"(expected: {args.input_dir / MANIFEST_FILE})")

    try:
        type_stats = count_scenarios_by_type(args.input_dir)
        if type_stats:
            rows = build_rows_from_split_data(type_stats, manifest)
        elif manifest:
            rows = build_rows_from_manifest(manifest)
        else:
            rows = [{
                "Fault Type": "PENDING", "Total": "PENDING", "Confounded": "PENDING",
                "Dev Split": "PENDING", "Val Split": "PENDING", "Test Split": "PENDING",
            }]

        write_csv(rows, args.output_dir / "table4_scenarios.csv")
        write_latex(rows, args.output_dir / "table4_scenarios.tex")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
