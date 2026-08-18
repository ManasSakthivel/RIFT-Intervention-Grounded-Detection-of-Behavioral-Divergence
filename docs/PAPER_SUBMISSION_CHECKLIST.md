# RIFT — Paper Submission Checklist (Synthetic-Only Evidence)
**Status:** MANDATORY — must be verified before any paper submission
**Authority:** P0-05, docs/CLAIMS_REGISTRY.yaml, docs/PHASE_3_SPEC_FREEZE.md §15

---

## Purpose

This checklist enforces the rule: **no live performance numbers may appear in
any paper draft without being labeled as SYNTHETIC BENCHMARK ONLY**, until
Category C evidence (live_telemetry_used=True RIFTRunRecord) exists.

This checklist must be signed off before any paper draft is submitted to a venue.

---

## Pre-Submission Checklist

### Table/Figure Verification

Before submission, for EVERY table and figure containing numerical results, verify:

```
□ Table/Figure N: "_________________________________"
  □ Numbers sourced from: [experiment_id]_[artifact_path]
  □ live_telemetry_used = [True / False]
  □ If False: labeled "SYNTHETIC BENCHMARK ONLY — Development Set, MockTelemetry"
  □ No live-system performance claims made from this table/figure
  □ Claim registry entry: [C00X] — status = [PLANNED/PARTIALLY_SUPPORTED/SUPPORTED]
```

### Required Labels for Synthetic Results

Any table or figure showing:
- P@1 values from development.json / MockTelemetry
- Detection latency from synthetic scenarios
- Intervention cost from dry-run execution
- Abstention rates from synthetic scenarios

MUST carry the label:

> "SYNTHETIC BENCHMARK ONLY — Development Set, MockTelemetry, Phase 3.5.
>  Live system results pending Linux experimental execution."

This label applies to:
- Table footnotes
- Figure captions
- Abstract phrases ("achieves P@1 = X.XX" must specify "synthetic" or "live")
- Introduction claims

### Frozen Historical Evidence

P@1 = 0.50 (raw), P@1 = 0.60 (conditional) from `artifacts/phase3_5/v1_decomposition.json`
are **FROZEN HISTORICAL EVIDENCE** from Phase 3.5 MockTelemetry evaluation.

These values:
- ✅ MAY be cited as: "synthetic pre-validation baseline (development set)"
- ❌ MUST NOT be presented as: live system performance
- ❌ MUST NOT appear in abstract as main results
- ❌ MUST NOT be compared with other papers' live results

---

## Status Upgrade Rules (Post-Linux)

After Linux execution, upgrade claim statuses as follows:

| Condition | From | To |
|-----------|------|----|
| EXP-001 runs with live_telemetry_used=True | PLANNED | SUPPORTED |
| EXP-002 runs with n≥48 confounded scenarios | PLANNED | SUPPORTED |
| EXP-005 ablation runs live | PLANNED | SUPPORTED |
| EXP-013 ablation runs live | PLANNED | SUPPORTED |
| EXP-014 ablation runs live | PLANNED | SUPPORTED |

Do NOT upgrade any claim until the corresponding experiment actually runs.

---

## Sign-Off

Before submission, the following must be confirmed:

```
□ All performance numbers in paper are from named experiments with known artifacts.
□ All synthetic numbers are labeled "SYNTHETIC BENCHMARK ONLY".
□ No claim in CLAIMS_REGISTRY has status=UNSUPPORTED in the paper.
□ SIEVE-LIKE is labeled "SIEVE-LIKE" in all tables (never "Sieve").
□ H5 (cross-system) does NOT appear in contributions or abstract.
□ P@1=0.50/0.60 not presented as live results.
□ RIFT-RANDOM total_ed_s comes from real intervention dispatch (P0-04 fixed).
□ Cliff's delta interpretation note included for binary P@1 outcomes (P1-07).
```

---

## Related Documents

- [`docs/CLAIMS_REGISTRY.yaml`](CLAIMS_REGISTRY.yaml) — all claim statuses
- [`docs/EXPLORATORY_COMPARISONS_REGISTRY.md`](EXPLORATORY_COMPARISONS_REGISTRY.md)
- [`docs/PHASE_3_SPEC_FREEZE.md`](PHASE_3_SPEC_FREEZE.md) §15
- [`src/rift/statistics/stats.py`](../src/rift/statistics/stats.py) — statistical implementation
