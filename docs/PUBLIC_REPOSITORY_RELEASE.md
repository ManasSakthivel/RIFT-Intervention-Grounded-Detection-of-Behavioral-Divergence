# RIFT — Public Repository Release Report

**Date:** 2026-08-18  
**Repository:** RIFT — Intervention-Grounded Detection of Behavioral Divergence  
**URL:** https://github.com/ManasSakthivel/RIFT-Intervention-Grounded-Detection-of-Behavioral-Divergence  

---

## Release Summary

| Item | Result |
|------|--------|
| Git commit | `56b8de2` |
| Tests | **624 PASS / 0 FAIL** |
| Files tracked | **313** |
| Files removed (junk) | `__pycache__/`, `.pytest_cache/`, `.bob/`, `.DS_Store`, `env.txt` |
| Secrets detected | **0** |
| README | COMPLETE (with 3 research diagrams) |
| Research diagrams | **3** (architecture, obs-vs-intervention, testbed topology) |
| Citation file | `CITATION.cff` — PASS |
| License | `LICENSE` (MIT) — PASS |
| Dataset licensing | Synthetic benchmark — original research artifacts, MIT |
| GitHub Actions CI | `.github/workflows/test.yml` — PASS |
| GitHub push | **SUCCESS** |

---

## What Was Done

### Security
- `env.txt` (hostname + password) **deleted** and added to `.gitignore`
- `.env` confirmed in `.gitignore` (not committed)
- PAT used for push then immediately removed from remote URL
- Full grep scan: `IBM!123` appears only as a CI scan pattern — no real secret committed
- `manas1.fyre.ibm.com` hostname present only in research provenance artifacts (expected)

### Repository structure
Existing structure was already well-organised. The following were added:

```
README.md                         — Complete research-first README
LICENSE                           — MIT + third-party attributions
CITATION.cff                      — CFF citation file
CONTRIBUTING.md                   — Contributor guidelines
CHANGELOG.md                      — Version history
.github/workflows/test.yml        — GitHub Actions CI (624 tests)
docs/figures/rift_architecture.svg    — RIFT pipeline diagram
docs/figures/obs_vs_intervention.svg  — Obs vs interventional reasoning
docs/figures/testbed_topology.svg     — Online Boutique topology
```

### Cleanup
| Removed | Reason |
|---------|--------|
| `__pycache__/` (all) | Generated Python bytecode |
| `.pytest_cache/` | Generated test cache |
| `.bob/` | IDE internal state |
| `env.txt` | **Credentials — deleted** |

### Files intentionally excluded (in .gitignore)
| Pattern | Reason |
|---------|--------|
| `env.txt` | VM credentials |
| `.env` | Environment secrets |
| `__pycache__/`, `*.pyc` | Python bytecode |
| `.pytest_cache/` | Test cache |
| `artifacts/logs/` | Runtime logs (large, ephemeral) |
| `results/*/raw_results.json` | Bulk experiment outputs |
| `.bob/` | IDE state |
| `.DS_Store` | macOS metadata |

---

## Linux Work Remaining

The next commit after this one will be the final Linux validation/results commit.

### Three known blockers (all fixes implemented and Mac-tested)

| ID | Blocker | Fix status |
|----|---------|-----------|
| T1 | `PrometheusClient.collect()` raises `NotImplementedError` — live_telemetry_used=False | Implemented, Mac-tested |
| T2 | Online Boutique v0.9.0 exposes gRPC only — Prometheus scrapes 0 boutique metrics | OTel collector wiring required |
| T3 | tc prio band `1:10` does not exist — fault injection aborted | Fixed to band `1:1` |

### Experiments pending Linux execution

| Experiment | Description |
|-----------|-------------|
| EXP-001 | RIFT-FULL on live Online Boutique telemetry (H1) |
| EXP-002 | H2 — 48 confounded scenarios with live tc/netem |
| EXP-003 | Intervention cost with live Prometheus |
| EXP-005 | RIFT-OBS ablation with live telemetry |
| EXP-006 | RIFT-RANDOM ablation with live interventions |
| EXP-007 | SIEVE-LIKE comparison with live telemetry |
| EXP-013 | H3 — RIFT-FULL vs RIFT-ONE-SHOT multi-cause |
| EXP-014 | H4 — MSIS vs random cost comparison |
| — | Held-out evaluation (15 sealed scenarios) |
| — | Final statistics, figures, tables |
| — | Evidence freeze, claim audit, hostile review |

---

## Final Repository Tree (top-level)

```
RIFT-Intervention-Grounded-Detection-of-Behavioral-Divergence/
├── README.md
├── LICENSE
├── CITATION.cff
├── CONTRIBUTING.md
├── CHANGELOG.md
├── Makefile
├── pyproject.toml
├── requirements.txt
├── conftest.py
├── .gitignore
├── .github/
│   └── workflows/test.yml
├── src/rift/              (22 modules)
├── tests/                 (624 tests)
├── datasets/rift_faults/  (development, validation, held_out, manifest)
├── experiments/           (REGISTRY.yaml, ablations)
├── configs/               (development, validation, held_out, live, dry_run)
├── analysis/              (figures, tables, scripts)
├── artifacts/             (phase3, phase3_5, phase4, pre_linux, freeze)
├── docs/                  (methodology, experiments, baselines, claims, figures)
├── docker/                (Dockerfile, compose, otel, prometheus)
├── scripts/               (start/stop/health/cleanup testbed)
└── validation/            (CID validation, harness)
```
