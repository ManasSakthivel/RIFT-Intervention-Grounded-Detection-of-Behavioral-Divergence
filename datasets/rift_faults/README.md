# RIFT Fault Dataset — `datasets/rift_faults/`

**Version:** Phase 3P  
**Seed:** 42 (fixed — do not change)  
**Authority:** `docs/PHASE_3_SPEC_FREEZE.md §15`, `docs/hypotheses.md`

---

## Overview

This directory contains the **RIFT synthetic ground-truth fault benchmark** for
Phases 3P (benchmark generation) and 3Q (statistical validation). It provides
reproducible, locked fault scenarios for evaluating RIFT's causal attribution
against explicitly known ground truth.

> **Critical protocol:** Ground truth is locked before any RIFT evaluation.  
> RIFT must NOT be tuned against individual fault scenarios after the dataset
> is split. Final evaluation uses the `HELD_OUT_TEST` split only.

---

## Topology

**System:** Google Online Boutique (11 services)

| Service | Role |
|---|---|
| `frontend` | Edge entry point; fan-out to all major services |
| `cart` | Shopping cart; depends on `redis_cart` |
| `checkout` | Order processing; calls `payment`, `shipping`, `email`, `cart`, `currency` |
| `payment` | Payment processor (leaf node) |
| `product_catalog` | Product listing (leaf node) |
| `recommendation` | Product recommendations; calls `product_catalog` |
| `shipping` | Shipping cost calculation (leaf node) |
| `email` | Confirmation email (leaf node) |
| `currency` | Currency conversion (leaf node) |
| `ad` | Advertisement service (leaf node) |
| `redis_cart` | Redis backing store for `cart` (leaf node) |

**Call graph (directed):**

```
frontend → cart, product_catalog, recommendation, shipping,
           currency, ad, checkout
checkout → payment, shipping, email, cart, currency
cart     → redis_cart
recommendation → product_catalog
```

---

## Fault Types

| Code | Description |
|---|---|
| `NETWORK_LATENCY` | Elevated network round-trip time; increases `lat_p99` |
| `PACKET_LOSS` | Dropped packets causing retries; raises `err_rate` |
| `SERVICE_DEGRADATION` | Process-level CPU spike or memory pressure |
| `RESOURCE_CONTENTION` | Shared resource (e.g., Redis) saturated |
| `QUEUEING` | Request queue approaches saturation (M/M/1 model) |
| `DEPENDENCY_FAILURE` | Upstream dependency crashes or returns errors |
| `MULTI_CAUSE` | Two simultaneous independent faults in the same window |
| `CONFOUNDED` | Shared latent variable (U_host) causes correlated anomalies |

---

## Dataset Splits

Splits are assigned deterministically at generation time with `seed=42`.  
Proportions: **50 % DEVELOPMENT · 25 % VALIDATION · 25 % HELD_OUT_TEST**.

| Split | Purpose | RIFT Access |
|---|---|---|
| `DEVELOPMENT` | Hyperparameter tuning, algorithm development | ✅ Full access |
| `VALIDATION` | Intermediate evaluation, ablation studies | ✅ Full access |
| `HELD_OUT_TEST` | Final paper results only | ❌ No access until evaluation freeze |

> **Protocol violation:** Using `HELD_OUT_TEST` scenarios to tune any RIFT
> parameter or threshold is a protocol violation. See
> `docs/PHASE_3_SPEC_FREEZE.md §15`.

---

## Ground-Truth Schema

Each `FaultScenario` is a frozen dataclass with the following fields:

| Field | Type | Description |
|---|---|---|
| `fault_id` | `str` | Unique identifier (e.g., `NL_01`, `CF_07`) |
| `name` | `str` | Human-readable description |
| `root_cause_service` | `str` | The service where the fault originates |
| `fault_type` | `str` | One of the 8 fault type codes above |
| `injected_at_t` | `float` | Seconds after window start when fault is injected |
| `expected_recovery_t` | `float` | Seconds after window start when fault resolves |
| `causal_path` | `List[Tuple[str,str]]` | Directed edges from root cause to effects |
| `confounded` | `bool` | `True` if scenario contains an unobserved common cause |
| `confounder_description` | `Optional[str]` | Human description of the latent variable |
| `affected_services` | `List[str]` | All services showing anomalous metrics |
| `observable_by_rift` | `bool` | `False` if root cause is outside RIFT's instrumentation boundary |
| `split` | `str` | `DEVELOPMENT` / `VALIDATION` / `HELD_OUT_TEST` |
| `ground_truth_locked` | `bool` | Always `True` in production scenarios |
| `seed` | `int` | Per-scenario random seed for `simulate_metrics` |

---

## Confounded Scenario Sub-Corpus (`C_confounded`)

The `CONFOUNDED` fault type implements **Hypothesis H2** from
`docs/hypotheses.md`:

> *"On the confounded fault subset C_confounded: Precision@1(RIFT-FULL) >
> Precision@1(RIFT-OBS) with p < 0.05 and Cliff's δ > 0.20"*

### Design rationale

Two services share a physical host. Host CPU saturation (latent variable
`U_host ∉ V`) causes correlated metric anomalies in both services
simultaneously. The correlation is **NOT causal** — neither service causes
the other's degradation. An observational method (RIFT-OBS) will see a
strong correlation and may attribute one as the cause of the other.
RIFT-FULL uses an active intervention: perturbing service A while holding B
constant. If B's metrics remain elevated, the link is confounded.

### Sample-size requirement

`docs/PHASE_3_SPEC_FREEZE.md §15` requires **≥ 48 confounded incidents**
for 80 % power on H2. If fewer are collected:

> *"Report achieved power only; do NOT claim 80%."*

The generator emits a `UserWarning` if fewer than 48 scenarios are created.
Check `achieved_power` from `check_power_achieved()` in
`src/rift/statistics/stats.py`.

### Confounded service pairs

| Pair | Confounder |
|---|---|
| `cart` ↔ `redis_cart` | Shared host memory / CPU |
| `payment` ↔ `email` | Shared host CPU |
| `recommendation` ↔ `product_catalog` | Shared host CPU |
| `shipping` ↔ `currency` | Shared host CPU |

---

## Metric Simulation

`SyntheticBenchmark.simulate_metrics()` returns per-service time series:

| Column | Unit | Description |
|---|---|---|
| `time` | seconds | Window-relative timestamp |
| `lat_p99` | ms | 99th-percentile request latency |
| `err_rate` | fraction [0,1] | Request error rate |
| `rps` | req/s | Requests per second |
| `cpu_pct` | % | CPU utilisation |
| `mem_pct` | % | Memory utilisation |

**Causal propagation model:**
- Root-cause service: immediate degradation at `injected_at_t`
- Downstream services: degradation delayed by `depth × Δt` where `Δt = 10 s`
  (one call-graph hop = one window; see `docs/PHASE_3_SPEC_FREEZE.md §2`)
- Confounded services: additive Gaussian noise from `U_host`; same magnitude,
  independent draw — **not** propagated through the call graph

**This simulation is independent of RIFT's own causal graph and is NOT used
as the oracle for RIFT's internal model.**

---

## Generating the Dataset

```python
from rift.benchmark.synthetic_benchmark import SyntheticBenchmark

bench = SyntheticBenchmark()

# All scenarios (primary + confounded, n ≥ 69)
all_faults = bench.generate_all_faults(seed=42)

# Confounded subset only (n=48 for 80% power on H2)
confounded = bench.generate_confounded_scenarios(n=48, seed=42)

# Simulate metrics for a single scenario
metrics = bench.simulate_metrics(all_faults[0])
# metrics["checkout"] → pd.DataFrame with columns [time, lat_p99, ...]
```

---

## Statistical Validation

The companion module `src/rift/statistics/stats.py` implements all
frozen tests from `docs/PHASE_3_SPEC_FREEZE.md §15`:

```python
from rift.statistics.stats import (
    wilcoxon_one_sided,    # H1, H2, H3, H4 (cost)
    tost_equivalence,      # H4 (accuracy)
    binomial_one_sided,    # H5
    cliffs_delta,          # always reported
    holm_bonferroni_correction,  # 6 confirmatory tests
    bh_fdr_correction,     # exploratory comparisons
    check_power_achieved,  # H2 power check
    run_confirmatory_tests, # convenience: all 6 tests + Holm correction
)
```

### Key invariants

- **Cliff's δ is always reported**, even when `p > 0.05`.
- All Wilcoxon tests are **one-sided** (`alternative='greater'`).
- Holm-Bonferroni is applied to all 6 confirmatory tests jointly.
- BH FDR is for exploratory comparisons only — never as primary evidence.
- Power is reported as `achieved_power`; `claim_80pct_power=True` only when
  `n_confounded ≥ 48`.

---

## Limitations

Consistent with `docs/PHASE_3_SPEC_FREEZE.md §17`:

| ID | Limitation |
|---|---|
| L1 | Unobserved confounding — RIFT abstains; does not force attribution |
| L4 | `observable_by_rift=False` scenarios test boundary-limited attribution |
| L9 | Online Boutique is not enterprise-scale; stated in all evaluation sections |
| L10 | Sub-millisecond systems out of scope (`Δt_min = 1 s`) |
| L11 | Silent logic errors out of scope (performance/availability faults only) |

---

## Prohibited Language

Per `docs/PHASE_3_SPEC_FREEZE.md §18`, the following phrases are **forbidden**
in any document or code comment referencing this dataset:

- ~~"causally accurate"~~
- ~~"correct causal graph"~~
- ~~"solves confounding"~~
- ~~"production-ready"~~
- ~~"guarantees causal attribution"~~

**Required phrases:**
- "intervention-consistent"
- "validated on synthetic ground-truth scenarios"
- "evaluated on Online Boutique"
- "RIFT abstains when..."
