# Phase 3.5 — Hostile Scientific Review Panel
**6 Independent Hostile Reviewers | Phase 3.5 Gate**

> **Panel question: "Can RIFT now legitimately be described as an integrated live-system research prototype?"**

---

## REVIEWER 1: Distributed Systems Expert

### Background
Expert in microservice observability, Docker networking, gRPC, and traffic shaping.

### P0 Issues
*None.*

### P1 Issues

**P1-DS-1: Prometheus scrapes gRPC ports — zero service metrics will be collected**
`docker/prometheus.yml` targets `boutique-cart:7070`, `boutique-product:3550`, etc. These are gRPC server ports, not HTTP `/metrics` endpoints. Online Boutique v0.9.0 uses OpenTelemetry → Jaeger. Prometheus will fail to scrape all boutique service targets. The entire metrics pipeline is blocked until this is resolved. Without service metrics, `G_T` has no variables, FCI cannot run, and the entire RIFT pipeline cannot execute. This is a **deployment blocker**.

**P1-DS-2: tc u32 on persistent gRPC connections**
Online Boutique services communicate via HTTP/2 gRPC with persistent connections. tc u32 filter applies to new packets. An already-established HTTP/2 connection will have its packets affected by the netem rule immediately, but the connection establishment RTT cannot be measured retroactively. The latency injection applies to in-flight packets but the service may not immediately detect the increased latency (e.g., if no requests are in flight at the moment of injection). The 5s measurement window after injection must account for request inter-arrival time.

**P1-DS-3: Service IP instability on container restart**
Docker bridge network assigns IPs from the subnet dynamically. Container restart changes the IP. tc rules are installed against the IP at injection time. A container restart after injection invalidates the tc rule target without triggering ROLLBACK_FAILURE (the rule persists but now affects a different or no container). The fault injector must re-verify the IP mapping before each injection.

### P2 Issues
- **P2-DS-1**: 10 Locust users is insufficient to establish stable baseline statistics for CID (Wasserstein W1 needs n ≥ 50 samples; at 10 users, at 10s Δt windows, sample size per window may be < 20 → INSUFFICIENT tier).
- **P2-DS-2**: Online Boutique loadgen behavior is non-stationary at startup; need 60-120s warmup before any baseline measurement.

### Verdict
Phase 3.5 correctly identifies that live-system validation is not yet achieved. The Prometheus/gRPC gap is a deployment blocker that must be resolved before any claim of "real telemetry" is valid.

---

## REVIEWER 2: Causal Inference Expert

### Background
Expert in causal discovery, PAG theory, identifiability, and intervention design.

### P0 Issues
*None — RIFT's causal claims are appropriately hedged.*

### P1 Issues

**P1-CI-1: Oracle PAG V1=50% is the upper bound; FCI-estimated PAG performance is unknown**
The validation harness uses an oracle PAG constructed directly from ground-truth causal paths. This bypasses FCI entirely. The actual V1 with FCI-estimated PAG from live telemetry is completely unknown. Given FCI's finite-sample limitations (especially with n=10 users → low sample count per window), the real V1 could be substantially below 50%. The paper cannot claim any performance figure without FCI-estimated PAG results.

**P1-CI-2: theta_cid = 0.1 * IQR_baseline is not pre-registered with justification**
The CID threshold was set without a pre-registered sensitivity analysis. At low sample sizes (n < 50), IQR_baseline has high variance, making theta_cid unstable. The threshold must be justified or a sensitivity analysis must be performed showing robustness across a reasonable range.

**P1-CI-3: R3 structural failure for leaf nodes is a fundamental methodological issue**
The decomposition (Agent F) shows that 4/6 failures are R3 leaf-node failures. R3 requires the candidate to have a downstream diverging service. But the call-graph PAG places callee services as sinks — they have no outgoing edges. This means RIFT **cannot identify root causes that are pure callees** (payment, product_catalog, redis) using oracle PAG. This is not a bug — it reflects a genuine limitation of the R3 criterion. The paper must state this limitation explicitly.

### P2 Issues
- **P2-CI-1**: Wasserstein W1 measures distributional distance, not causal effect magnitude. The connection between W1 and causal effect is asserted but not formally derived. The paper should state "W1 is used as a proxy for distribution shift consistent with a causal effect" rather than implying it directly measures the causal effect.
- **P2-CI-2**: The identifiability criterion (backdoor/frontdoor/IV) requires knowing the full causal structure. RIFT has only a PAG with uncertain orientations. The identifiability check on a PAG returns a conservative (possibly incorrect) verdict — this is documented but must be stated prominently.

### Verdict
RIFT's causal methodology is scientifically careful. The key gap is unknown FCI-estimated performance. The R3 leaf-node limitation must be addressed (via relaxed R3 or reverse-edge augmentation) or prominently documented as a scope limitation before Phase 4.

---

## REVIEWER 3: ICSE Empirical Software Engineering

### Background
Expert in empirical evaluation, benchmarks, and measurement validity.

### P0 Issues
*None.*

### P1 Issues

**P1-ES-1: n=12 non-confounded scenarios is too small for P@1 claims**
The 95% Wilson confidence interval for P@1=0.5 with n=12 is approximately [0.24, 0.76]. This overlaps substantially with random guessing (0.5) and makes it impossible to draw statistically meaningful conclusions about RIFT's precision. The DEVELOPMENT split needs more non-confounded scenarios, or the paper must present only the VALIDATION split results (n=18, 6 non-confounded) with wide confidence intervals.

**P1-ES-2: No baseline comparison executed**
`RIFT-RANDOM` and `RIFT-OBS` ablations are defined but not executed. Without baseline comparison, there is no evidence that RIFT's intervention-based approach improves over pure observational RCA. This is a core claim of the paper and cannot be deferred to Phase 4.

**P1-ES-3: Synthetic benchmark generated by the same team**
The 69-scenario benchmark was generated by `SyntheticBenchmark` in `src/rift/benchmark/synthetic_benchmark.py` — the same codebase as RIFT. This creates a risk of benchmark leakage: the scenario structure may implicitly favor RIFT's approach. An independent benchmark (e.g., from the Chaos Engineering literature) is needed for the final evaluation.

### P2 Issues
- **P2-ES-1**: Online Boutique is a demonstration app, not a production workload. Its service topology is simple (10 services, tree-like dependencies). Production microservices have 50-500 services, complex fan-out, and feedback loops. The paper must explicitly scope the evaluation to "small-scale distributed testbed" and not generalize.
- **P2-ES-2**: The reproducibility guide documents two tiers (macOS Python-only vs Linux full). But the Python-only tier does not exercise the intervention mechanism at all. Reviewers cannot reproduce the core claim without Linux.

### Verdict
The evaluation infrastructure is competently built but the sample sizes are too small for meaningful statistical claims. Baseline comparison is required before Phase 4. The paper must be scoped explicitly to small-scale testbeds.

---

## REVIEWER 4: Statistician

### Background
Expert in hypothesis testing, multiple comparisons, and statistical validity.

### P0 Issues
*None.*

### P1 Issues

**P1-ST-1: V1=50% on n=12 is not statistically distinguishable from random guessing**
The 95% CI is [0.21, 0.79] (Wilson). A random classifier that always picks the service with the highest anomaly score achieves P@1 ≈ 1/N ≈ 10-30% depending on N (number of candidate services). A naive "pick the service with highest anomaly score" baseline may achieve 40-60% P@1 by coincidence. Without testing against this baseline, the 50% figure is uninterpretable.

**P1-ST-2: FAR=33.3% on n=12 is n=4 events — no statistical power**
Four false attributions on twelve scenarios is not a stable estimate of FAR. The confidence interval is [0.12, 0.65]. This cannot be reported as a meaningful metric without more scenarios.

**P1-ST-3: Power analysis for H2 (80% power on 48 confounded scenarios) needs verification**
The manifest claims 80% power for H2 with 48 confounded scenarios. The power calculation's assumed effect size, α, and test statistic are not documented in the visible artifacts. This calculation must be shown and verified.

### P2 Issues
- **P2-ST-1**: Holm-Bonferroni and Benjamini-Hochberg are implemented for within-experiment multiple testing but not applied across the V1-V5 validation metrics themselves.
- **P2-ST-2**: The permutation test (B=10000) for CID is applied to simulated data in unit tests. It has not been validated on real telemetry where autocorrelation and non-stationarity can invalidate i.i.d. permutation assumptions.

### Verdict
The statistical infrastructure is carefully implemented. The primary issue is that sample sizes in the validation split are too small for reliable estimates. Phase 4 must target n ≥ 30 per condition for meaningful confidence intervals.

---

## REVIEWER 5: Reproducibility Expert

### Background
Expert in computational reproducibility, software artifact evaluation.

### P0 Issues
*None.*

### P1 Issues

**P1-RE-1: Python version inconsistency between artifact and environment**
`artifacts/phase3/PHASE_3_MANIFEST.json` records `"python_version": "3.9.6"` but `pyproject.toml` requires `>=3.10` and `docker/Dockerfile` uses Python 3.11. A researcher reproducing on Python 3.9.6 may encounter incompatibilities. The manifest must be regenerated on 3.11, or the version discrepancy must be explained.

**P1-RE-2: Linux required for core claim but documentation tier separation is weak**
The README/reproduction guide documents Tier 1 (Python only, any OS) and Tier 2 (Linux, full testbed). But the core RIFT contribution — closed-loop intervention — is only reproducible in Tier 2. A researcher reading the paper and running `make test` would see 453 PASS but none of the paper's core experiments would have been reproduced. This must be made explicit: "Running `make test` does NOT reproduce the paper's experiments."

### P2 Issues
- **P2-RE-1**: `SyntheticBenchmark.generate_all_faults(seed=42)` — dict ordering in Python 3.7+ is insertion-ordered, so this should be deterministic. But numpy RNG behavior can vary between numpy versions. The `requirements.txt` should pin numpy and scipy precisely.
- **P2-RE-2**: The docker-compose file uses `gcr.io/google-samples` images. If Google deprecates these images or changes v0.9.0 digests, reproduction fails. Pin images by digest (`@sha256:...`) for long-term reproducibility.

### Verdict
Reproducibility documentation is thorough and honest about macOS limitations. The Python version inconsistency and the "make test = paper reproduction" confusion must be fixed before submission.

---

## REVIEWER 6: Security / Safety Expert

### Background
Expert in security properties of automated systems, adversarial testing, and safety-critical software.

### P0 Issues
*None.*

### P1 Issues

**P1-SA-1: SAFE_ABORT during INTERVENE does not guarantee rollback was called**
If the safety controller returns SAFE_ABORT while the intervention engine is mid-execution (between the prio qdisc add and the u32 filter add), the `rollback_all()` method has not yet been called. The closed_loop.py state machine transitions to SAFE_ABORT but does not explicitly call rollback_all(). The tc rule may be partially installed. This is a safety gap: the system claims to abort safely but may leave an active partial tc rule.

**P1-SA-2: DATA_MUTATION check relies on caller setting the field**
The `DATA_MUTATION_ATTEMPT` hard stop checks `getattr(candidate, 'mutates_data', False)`. If a caller constructs an `InterventionCandidate` without setting this field (which defaults to False), the check is bypassed silently. The hard stop should be enforced at the `InterventionCandidate` model level via a field validator, not relying on caller discipline.

### P2 Issues
- **P2-SA-1**: Cascade failure threshold is `error_rate > 50% for > 30s`. In a 10-user test environment, a single request failure can push error_rate to 100% momentarily. The 30s duration requirement prevents false positives, but 30s of 50%+ error rate in a research testbed is a long time to wait before aborting.
- **P2-SA-2**: The kill-switch (`_kill_switch_activated`) is an instance variable. If the SafetyController instance is garbage collected and recreated (e.g., in tests), the kill-switch is reset. In a real deployment, the kill-switch state must persist across process restarts (e.g., written to a file or environment variable).
- **P2-SA-3**: The `rollback_attempts > 3` threshold for ROLLBACK_FAILURE triggers even if rollback ultimately succeeded (the current implementation checks `attempts > max_attempts` before the `rollback_succeeded` check was intended to OR with it). The logic is correct as written (both conditions trigger abort) but the semantics should be: abort if `not succeeded OR attempts > 3`.

### Verdict
The safety model is thoughtfully designed. The two P1 issues (SAFE_ABORT without rollback guarantee, DATA_MUTATION reliance on caller discipline) should be fixed before live deployment. The kill-switch persistence issue is important for production but acceptable for research prototype use.

---

## Panel Summary

### Total P0 Issues: 0

### Total P1 Issues: 11

| ID | Reviewer | Issue |
|---|---|---|
| P1-DS-1 | Distributed Systems | Prometheus scrapes gRPC ports — zero service metrics |
| P1-DS-2 | Distributed Systems | tc u32 on persistent gRPC connections |
| P1-DS-3 | Distributed Systems | Service IP instability on container restart |
| P1-CI-1 | Causal Inference | Oracle PAG V1 is upper bound; FCI performance unknown |
| P1-CI-2 | Causal Inference | theta_cid not pre-registered |
| P1-CI-3 | Causal Inference | R3 leaf-node failure is fundamental |
| P1-ES-1 | Empirical SE | n=12 too small for P@1 claims |
| P1-ES-2 | Empirical SE | No baseline comparison executed |
| P1-ES-3 | Empirical SE | Benchmark generated by same team |
| P1-ST-1 | Statistics | V1=50% on n=12 indistinguishable from random |
| P1-RE-1 | Reproducibility | Python version inconsistency |
| P1-RE-2 | Reproducibility | make test ≠ paper reproduction |
| P1-SA-1 | Safety | SAFE_ABORT during INTERVENE doesn't guarantee rollback |
| P1-SA-2 | Safety | DATA_MUTATION relies on caller discipline |

### Total P2 Issues: 8
*See individual reviewer sections above.*

---

## Consensus Verdict

> **"Can RIFT now legitimately be described as an integrated live-system research prototype?"**

**NO — not yet.**

RIFT is a **well-implemented synthetic-validated prototype with a specified live-system architecture.**

The following conditions prevent the "live-system" label:

1. **No live telemetry**: The Prometheus/gRPC port mismatch means no real service metrics can flow. G_T cannot be constructed from live data.
2. **No live intervention**: tc/netem has not been executed on Linux. The intervention remains dry-run only.
3. **No live deployment**: Online Boutique has not been deployed and health-checked.
4. **Unknown FCI performance**: V1 with FCI-estimated PAG from live telemetry is completely unknown.
5. **No baseline comparison**: RIFT-RANDOM and RIFT-OBS ablations are not executed.

**What RIFT legitimately is:** A fully specified, comprehensively unit-tested research prototype that correctly implements causal inference, safety hard stops, and a closed-loop intervention design. The synthetic validation is careful and honest. The architecture for live-system operation is specified and could be executed with the identified fixes.

## Required Actions Before Phase 4

1. Resolve Prometheus/gRPC port mismatch (P1-DS-1) — add OTEL Collector or cadvisor
2. Deploy and health-check Online Boutique on Linux
3. Execute at least one live E2E run with real telemetry (live_telemetry_used=True)
4. Verify tc intervention with independent measurement on Linux + CAP_NET_ADMIN
5. Execute RIFT-RANDOM and RIFT-OBS ablation baselines
6. Fix SAFE_ABORT→rollback_all() integration (P1-SA-1)
7. Fix DATA_MUTATION model-level enforcement (P1-SA-2)
8. Increase non-confounded test scenarios to n ≥ 30 for meaningful P@1 estimates
