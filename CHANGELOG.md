# Changelog

All notable changes are documented here.

## [0.1.0-phase4] — 2026-08-17

### Added
- Linux Phase 4 execution: RHEL 9.6, Docker 29.7.2, all 14 Online Boutique containers healthy
- tc/netem intervention infrastructure validated on Linux kernel 5.14 (T3 fix: band index)
- All 8 safety hard stops validated on live Linux environment
- Phase 4 artifacts: environment, testbed health, telemetry validation, intervention records
- RIFT-ONE-SHOT baseline implementation (P0-01 fix)
- RIFT-RANDOM intervention dispatch (P0-04 fix)
- EBD leaf-node R3 fallback (P1-11 fix)
- H2 power target met: 48 confounded scenarios across development + validation splits (P0-03 fix)
- H3 n=15 multi-cause/ambiguous scenarios in development set (P0-02 fix)
- Closed-loop posterior update provenance documentation (P1-12 fix)
- Exploratory comparisons registry (P2-07 fix)
- 31 new tests: RIFT-RANDOM dispatch (15), EBD leaf-node R3 (16)

### Fixed
- P0-04: RIFT-RANDOM previously hardcoded `total_intervention_ed_s=0.0`
- P0-02: H3 had only n=1 multi-cause scenario — Wilcoxon undefined
- P0-03: H2 power requirement (48 confounded) not met from development set alone
- P1-11: R3 criterion failed for leaf-node sink services in call-graph PAG
- P1-09: EXP-014 non-standard statistical_test keys
- T3: tc band handle `1:10` → correct `1:1` for default prio qdisc

### Known blockers (pending next Linux run)
- T1: `PrometheusClient.collect()` is unimplemented stub — live_telemetry_used=False
- T2: Online Boutique v0.9.0 gRPC-only — Prometheus scrape targets show 0 boutique metrics
- T3: tc band fix implemented and Mac-tested; not yet re-run on Linux

## [0.1.0-phase3] — 2026-08-15

### Added
- Complete RIFT pipeline: FCI/PAG, anomaly subgraph, identifiability, EBD, CID, MSIS, closed-loop
- Synthetic development benchmark: 36 scenarios (later expanded to 50)
- Phase 3.5 V1 analysis: raw P@1=50%, conditional P@1=60%, V2 abstention=100%
- All baselines: RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, ORACLE
- Safety controller: 8 hard stops with dry-run validation
- Experiment registry (14 experiments), claims registry (13 claims)
- Statistical pipeline: Wilcoxon, TOST, binomial, Holm-Bonferroni, BH-FDR
- 593 tests passing at phase freeze
