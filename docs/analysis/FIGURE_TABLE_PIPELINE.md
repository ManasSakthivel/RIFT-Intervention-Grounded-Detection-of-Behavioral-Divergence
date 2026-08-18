# Figure and Table Generation Pipeline
Phase: parallel-sprint
Owner: Agent 7

## Overview

This pipeline contains standalone Python generators that produce every paper figure and
table for RIFT from machine-readable result artifacts.  The generators are designed so
that the paper-building pipeline never blocks: when experiment results are not yet
available, each generator emits a clearly-labelled placeholder output and exits with
code `0`.

Key design invariants:
- **No hardcoded numbers.** Every numeric value in an output is read from a JSON/CSV
  artifact in `results/` or `datasets/`.
- **Graceful degradation.** Missing inputs produce a template/placeholder file rather
  than failing the build.
- **Deterministic.** Fixed numpy random seeds are used wherever randomness is needed
  (currently only in the H2 power curve, which is fully analytical).
- **Headless-safe.** All matplotlib figures use the `Agg` backend; no display is needed.

---

## Figures

| Figure | File | Inputs | Outputs | Status |
|--------|------|--------|---------|--------|
| Fig 1 — Precision@1 bar chart | [`analysis/figures/fig1_rq_precision.py`](../../analysis/figures/fig1_rq_precision.py) | `results/EXP-001/results.json` | `fig1_rq_precision.{png,pdf,csv}` | ✅ Template-ready |
| Fig 2 — Baseline comparison | [`analysis/figures/fig2_baseline_comparison.py`](../../analysis/figures/fig2_baseline_comparison.py) | `results/EXP-001,005,007/results.json` | `fig2_baseline_comparison.{png,pdf}` | ✅ Template-ready |
| Fig 3 — Ablation results | [`analysis/figures/fig3_ablation.py`](../../analysis/figures/fig3_ablation.py) | `results/EXP-005,006,013/results.json` | `fig3_ablation.{png,pdf}` | ✅ Template-ready |
| Fig 4 — Runtime/intervention cost | [`analysis/figures/fig4_runtime.py`](../../analysis/figures/fig4_runtime.py) | `results/EXP-009,003/results.json` | `fig4_runtime.{png,pdf}` | ✅ Template-ready |

### Existing generators (Phase 4.5)

The file [`analysis/figures/generate_figures.py`](../../analysis/figures/generate_figures.py)
contains the original monolithic figure generator from Phase 4.5.  The new per-figure
scripts above are preferred for incremental regeneration and CI integration.  Both sets
of scripts can coexist.

---

## Tables

| Table | File | Inputs | Outputs | Status |
|-------|------|--------|---------|--------|
| Table 1 — Main results | [`analysis/tables/table1_main_results.py`](../../analysis/tables/table1_main_results.py) | `results/EXP-001/results.json` | `table1_main_results.{tex,csv}` | ✅ Template-ready |
| Table 2 — Ablation | [`analysis/tables/table2_ablation.py`](../../analysis/tables/table2_ablation.py) | `results/EXP-005,006,013/results.json` | `table2_ablation.{tex,csv}` | ✅ Template-ready |
| Table 3 — Statistical tests | [`analysis/tables/table3_statistics.py`](../../analysis/tables/table3_statistics.py) | `results/statistical_tests.json` | `table3_statistics.{tex,csv}` | ✅ Template-ready |
| Table 4 — Scenario summary | [`analysis/tables/table4_scenarios.py`](../../analysis/tables/table4_scenarios.py) | `datasets/rift_faults/manifest.json` + split files | `table4_scenarios.{tex,csv}` | ✅ Live data |

### Existing generators (Phase 4.5)

The file [`analysis/tables/generate_tables.py`](../../analysis/tables/generate_tables.py)
is the original Phase 4.5 monolithic table generator.  The new per-table scripts are
preferred for incremental runs.

---

## Running the Pipeline

### Regenerate everything

```bash
# From the workspace root
cd "/Users/manassakthivel/Desktop/SF Projects/untitled folder"

# --- Figures ---
python3 analysis/figures/fig1_rq_precision.py
python3 analysis/figures/fig2_baseline_comparison.py
python3 analysis/figures/fig3_ablation.py
python3 analysis/figures/fig4_runtime.py

# --- Tables ---
python3 analysis/tables/table1_main_results.py
python3 analysis/tables/table2_ablation.py
python3 analysis/tables/table3_statistics.py
python3 analysis/tables/table4_scenarios.py
```

### Override input/output directories

Every generator accepts `--input-dir` and `--output-dir`:

```bash
python3 analysis/figures/fig1_rq_precision.py \
    --input-dir /path/to/results \
    --output-dir /path/to/output
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success (may be template output if results absent) |
| `1`  | Unexpected error (see stderr) |

---

## Expected Result Artifact Schema

Each experiment's `results.json` should follow this shape:

```json
{
  "rift_full_raw_p1": 0.82,
  "rift_full_cond_p1": 0.91,
  "rift_full_abstention_rate": 0.10,
  "rift_full_mean_latency_s": 23.4,
  "rift_obs_raw_p1": 0.71,
  ...
}
```

For ablation experiments (`EXP-005`, `EXP-006`, `EXP-013`), the top-level keys are:

```json
{
  "raw_p1": 0.71,
  "cond_p1": 0.84,
  "wilcoxon_p": 0.003,
  "cliffs_delta": 0.42,
  "significant": true
}
```

Statistical tests are read from `results/statistical_tests.json` or
`results/statistics/confirmatory_tests.json`:

```json
{
  "tests": {
    "H1": {
      "test_name": "Wilcoxon signed-rank",
      "statistic": 1234.5,
      "pvalue": 0.0012,
      "cliffs_delta": 0.48,
      "cliffs_delta_ci": [0.31, 0.62],
      "significant": true
    },
    ...
  }
}
```

---

## Adding New Outputs

1. Create `analysis/figures/figN_<name>.py` or `analysis/tables/tableN_<name>.py`.
2. Follow the skeleton:
   - `load_results(path)` → returns `None` when the file is absent.
   - `generate_figure(results, output_dir)` / `build_rows(data)` — handles `None` by
     writing a placeholder and printing `"RESULTS NOT YET AVAILABLE — ..."`.
   - `main()` with `--input-dir` / `--output-dir` argparse arguments.
   - `if __name__ == "__main__": sys.exit(main())`
3. Add the new entry to this document's Figures or Tables table.
4. Add the run command to the "Regenerate everything" section.

---

## No-Hardcoded-Numbers Policy

**Rule:** Any numeric value that appears in a figure axis, bar height, table cell, or
annotation must be derived from a loaded artifact at runtime.  It must never be typed
into the Python source as a literal.

**Enforcement checklist:**

- [ ] Grep for bare floats in generator files:
  ```bash
  grep -n '\b0\.[0-9]\+\b' analysis/figures/*.py analysis/tables/*.py
  ```
  Each match must be either a visual constant (axis limit, line width) or a
  statistical parameter defined in a named constant with a comment.
- [ ] All generators must print `"RESULTS NOT YET AVAILABLE"` when input is absent.
- [ ] Generated outputs in version control must be template/placeholder files only
  until real experiments have run.

Permitted numeric literals in source:
- Axis range limits (`ylim(0, 1.05)`)
- Figure size and DPI (`figsize=(8, 4)`, `dpi=150`)
- Line widths and alpha values
- Holm-Bonferroni alpha boundary formula constants (`0.05 / k`)
- The H2 power curve analytic parameters (documented in the source and cross-referenced
  to `docs/hypotheses.md`)

---

## Status

**PASS** — All 8 generators exit `0` with no results present and produce placeholder
output files.  Table 4 reads live data from `datasets/rift_faults/` and produces a
correct 9-row summary (7 fault types + TOTAL).
