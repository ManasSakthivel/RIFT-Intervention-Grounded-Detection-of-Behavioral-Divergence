# Claim Audit
Phase: parallel-sprint
Auditor: Agent 8

---

## Executive Summary

```
CLAIMS_AUDITED:    13
SUPPORTED:          2   (C011, C012 — Category A infrastructure only)
PARTIALLY_SUPPORTED: 4  (C003, C007, C008, C009)
PLANNED:            6   (C001, C002, C004, C005, C006, C010*)
UNSUPPORTED:        1   (C013)

MISCLASSIFIED:      1   (C010 — registry calls it PARTIALLY_SUPPORTED but it carries no
                         live evidence whatsoever and is FROZEN HISTORICAL EVIDENCE;
                         it should be classified PLANNED/SYNTHETIC_ONLY with explicit
                         freeze notation — see C010 audit entry below)

SCOPE_VIOLATIONS:   3   (C006: SIEVE-LIKE labeling must be enforced;
                         C010: synthetic values must never surface as live results;
                         C002: n<48 confounded scenarios breaks H2 power requirement)
```

> **Overall status: BLOCKED — no Category C evidence exists. Paper MUST NOT assert
> live results, live attribution accuracy, statistical significance for H1–H5, or
> "live operation" for any claim until Phase 5 Linux E2E with live_telemetry_used=True.**

---

## Per-Claim Audit

---

### C001

```
CLAIM_ID:         C001
CLAIM:            "RIFT performs causal attribution on live distributed microservice systems."
RQ:               RQ1
EXPERIMENT:       EXP-001
ARTIFACT:         results/EXP-001/ (does not yet exist — PLANNED)
METRIC:           precision_at_1
CURRENT_STATUS:   PLANNED  (registry)
CORRECT_STATUS:   PLANNED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (synthetic only — no Category C exists)
LIMITATION_L1:    Requires live Online Boutique on Linux with T1+T2+T3 fixes deployed
LIMITATION_L2:    Current evidence is synthetic only (Category B)
LIMITATION_L3:    P@1=0.50 (synthetic dev set) must not be presented as live system performance
CLASSIFICATION:   PLANNED  — MUST NOT appear in paper as a result
NOTES:
  - Absolute Rule 1 violation risk: this claim asserts "live operation."
    No RIFTRunRecord with live_telemetry_used=True has been produced (T1/T2/T3
    not yet deployed on Linux). Publishing this claim as a result would be a
    Category C fabrication error.
  - EXP-001 status in REGISTRY.yaml is READY_FOR_LINUX — correctly reflects
    that code is ready but execution has not occurred.
  - RQ_EXPERIMENT_MAP.md confirms: READY_FOR_LINUX, not COMPLETE.
  - No misclassification in registry; PLANNED is correct.
```

---

### C002

```
CLAIM_ID:         C002
CLAIM:            "RIFT achieves higher Precision@1 than observational baselines on confounded incidents."
RQ:               RQ2
EXPERIMENT:       EXP-002
ARTIFACT:         results/EXP-002/ (does not yet exist — PLANNED)
METRIC:           conditional_precision_at_1
CURRENT_STATUS:   PLANNED  (registry)
CORRECT_STATUS:   PLANNED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (no live run — EXP-002 READY_FOR_LINUX, not COMPLETE)
LIMITATION_L1:    Requires n>=48 confounded scenarios for 80% power
LIMITATION_L2:    Requires live execution
LIMITATION_L3:    H2 is the CRITICAL hypothesis — if not confirmed, N2 claim collapses
CLASSIFICATION:   PLANNED  — MUST NOT appear in paper as a result

SCOPE VIOLATION — POWER REQUIREMENT:
  EXP-002 (REGISTRY.yaml) sets n_confounded_required=48 but n_scenarios=36 (development set).
  The development set manifest claims 48 confounded scenarios in RQ_EXPERIMENT_MAP.md
  ("datasets/rift_faults/manifest.json records 48 confounded scenarios in the development
  set"), however EXP-002 itself specifies n_scenarios=36. This is an internal inconsistency:
  either the full 48-scenario confounded subset exists and EXP-002 must be run against it,
  or there are only 36 development scenarios total, which is below the 80% power threshold.
  This inconsistency must be resolved before Linux execution. Running H2 on <48 confounded
  scenarios must report achieved power only — not claim 80% power.

NOTES:
  - Absolute Rule 3: no "final baseline superiority" claim before H2 Wilcoxon runs on real data.
  - RIFT-OBS implementation is noted as PARTIAL in the registry; must be confirmed complete
    before Linux run.
```

---

### C003

```
CLAIM_ID:         C003
CLAIM:            "RIFT correctly abstains on non-identifiable causal queries."
RQ:               RQ2
EXPERIMENT:       EXP-002
ARTIFACT:         artifacts/phase3_5/v1_decomposition.json
METRIC:           correct_abstention_rate
CURRENT_STATUS:   PARTIALLY_SUPPORTED  (registry)
CORRECT_STATUS:   PARTIALLY_SUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (synthetic validation — MockTelemetry, not live)
LIMITATION_L1:    Synthetic validation only — not live
LIMITATION_L2:    Non-identifiable scenarios use synthetic confounders
CLASSIFICATION:   SUPPORTED_WITH_SCOPE
  → In paper: must appear with explicit caveat:
    "Abstention logic validated on synthetic non-identifiable scenarios (Category B,
    MockTelemetry, 36 dev scenarios). Live validation pending."

NOTES:
  - This claim is the weakest form of "live system" assertion — it is a pipeline
    logic validation, not a behavioral claim about live traffic. SUPPORTED_WITH_SCOPE
    is appropriate provided the caveat is included.
  - Artifact (v1_decomposition.json) is FROZEN HISTORICAL EVIDENCE — do not modify.
  - No absolute rule violations as long as "live" language is excluded.
```

---

### C004

```
CLAIM_ID:         C004
CLAIM:            "RIFT's greedy MSIS cost optimizer achieves lower detection latency than random selection."
RQ:               RQ6
EXPERIMENT:       EXP-014
ARTIFACT:         results/EXP-014/ (does not yet exist — PLANNED)
METRIC:           total_ed_s, detection_latency_s
CURRENT_STATUS:   PLANNED  (registry)
CORRECT_STATUS:   PLANNED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (no live run — EXP-014 READY_FOR_LINUX, not COMPLETE)
LIMITATION_L1:    Requires live execution
LIMITATION_L2:    H4 requires TOST equivalence on accuracy AND one-sided Wilcoxon on cost
CLASSIFICATION:   PLANNED  — MUST NOT appear in paper as a result

NOTES:
  - Absolute Rule 3: no "final baseline superiority" claim before H4 TOST/Wilcoxon runs.
  - Absolute Rule 4: no "statistical significance" assertion without the corresponding
    tests running on real data.
  - EXP-014 (REGISTRY.yaml) correctly specifies two separate tests:
    statistical_test_cost=wilcoxon_one_sided and statistical_test_accuracy=tost_equivalence.
    Both must be applied with Holm-Bonferroni correction as specified in RQ_EXPERIMENT_MAP.md.
  - Note: REGISTRY.yaml maps EXP-014 to hypothesis H4, but docs/hypotheses.md maps H4 to
    EXP-014 (consistent). However, docs/hypotheses.md maps H3 to EXP-013 and RQ_EXPERIMENT_MAP
    maps H3 to EXP-013 — all consistent. No conflict.
```

---

### C005

```
CLAIM_ID:         C005
CLAIM:            "RIFT's intervention layer provides measurable information beyond observational analysis (RIFT > RIFT-OBS)."
RQ:               RQ1
EXPERIMENT:       EXP-005
ARTIFACT:         results/EXP-005/ (does not yet exist — PLANNED)
METRIC:           precision_at_1 delta (RIFT-FULL vs RIFT-OBS)
CURRENT_STATUS:   PLANNED  (registry)
CORRECT_STATUS:   PLANNED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (no live run — EXP-005 READY_FOR_LINUX, not COMPLETE)
LIMITATION_L1:    Requires live execution
LIMITATION_L2:    RIFT-OBS uses observational correlation proxy (PARTIAL implementation)
LIMITATION_L3:    Core novelty claim — if not confirmed, paper's thesis is weakened
CLASSIFICATION:   PLANNED  — MUST NOT appear in paper as a result

NOTES:
  - This is the paper's core novelty claim and maps directly to H1 (via EXP-005 ablation)
    and H2 (via EXP-002). Both are PLANNED. The claim cannot be made until both live
    experiments confirm the delta is non-zero and statistically significant.
  - RIFT-OBS partial implementation is a pre-Linux blocker: must be confirmed complete
    before EXP-005 runs.
  - Critical: if H2 fails (RIFT-FULL ≯ RIFT-OBS on confounded subset), this claim
    requires re-scoping. The paper thesis depends on this experiment.
```

---

### C006

```
CLAIM_ID:         C006
CLAIM:            "RIFT outperforms Sieve-like observational ranking on causal attribution accuracy."
RQ:               RQ1
EXPERIMENT:       EXP-007
ARTIFACT:         results/EXP-007/ (does not yet exist — PLANNED)
METRIC:           precision_at_1
CURRENT_STATUS:   PLANNED  (registry)
CORRECT_STATUS:   PLANNED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (no live run — EXP-007 READY_FOR_LINUX, not COMPLETE)
LIMITATION_L1:    Requires live execution
LIMITATION_L2:    Comparison is SIEVE-LIKE (methodological reimplementation), NOT original Sieve code
LIMITATION_L3:    Must be labeled SIEVE-LIKE in all tables — never "Sieve"
CLASSIFICATION:   PLANNED  — MUST NOT appear in paper as a result

SCOPE VIOLATION — LABELING:
  The claim text says "Sieve-like observational ranking" which is correct, but
  the risk is in any downstream paper draft or table that abbreviates this to "Sieve."
  EXP-007 (REGISTRY.yaml) carries the required label:
    "SIEVE-LIKE — NOT SIEVE. Methodological reimplementation."
  This label MUST propagate to every table, figure caption, and comparison statement
  in all paper drafts. No claim about the original Sieve system (Bhatt et al.) may
  be derived from this comparison.

NOTES:
  - Absolute Rule 3 applies: no superiority claim before H1 Wilcoxon runs.
  - If published with "Sieve" labeling instead of "SIEVE-LIKE," this becomes a
    misrepresentation of prior work — a P0 integrity risk.
```

---

### C007

```
CLAIM_ID:         C007
CLAIM:            "RIFT's causal graph (FCI-PAG) approximates the true causal structure."
RQ:               RQ3
EXPERIMENT:       EXP-004
ARTIFACT:         artifacts/phase3/fci_validation.json
METRIC:           oracle_vs_fci comparison
CURRENT_STATUS:   PARTIALLY_SUPPORTED  (registry)
CORRECT_STATUS:   PARTIALLY_SUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (synthetic FCI vs Oracle — Category B per PHASE4_EVIDENCE_RECONCILIATION.md)
LIMITATION_L1:    Synthetic validation only
LIMITATION_L2:    FCI may produce cycles or empty PAGs on sparse data
LIMITATION_L3:    Faithfulness assumption may be violated in real microservice traffic
CLASSIFICATION:   SUPPORTED_WITH_SCOPE
  → In paper: must appear with caveat:
    "FCI-PAG approximation validated against oracle on synthetic ground-truth graphs
    (Category B). Faithfulness assumption is untested on live microservice traffic."

NOTES:
  - PHASE4_EVIDENCE_RECONCILIATION.md confirms artifact path is
    artifacts/phase4/oracle_vs_fci/comparison.json (not artifacts/phase3/fci_validation.json
    as listed in registry). This is a minor path discrepancy — both files may exist but
    the Phase 4 artifact supersedes. Registry should be clarified.
  - EXP-004 status is DRY_RUN_READY, not READY_FOR_LINUX — meaning it can run on Mac
    in synthetic mode. This is consistent with Category B classification.
  - PAPER_EVIDENCE_MATRIX.md maps this to RQ1 (not RQ3) for the artifact
    artifacts/phase3/oracle_vs_fci.json. The RQ mapping is inconsistent between
    CLAIMS_REGISTRY.yaml (RQ3) and PAPER_EVIDENCE_MATRIX.md (RQ1). Must be resolved
    before paper submission.
```

---

### C008

```
CLAIM_ID:         C008
CLAIM:            "RIFT satisfies all 8 safety hard stops under adversarial conditions."
RQ:               null
EXPERIMENT:       EXP-008
ARTIFACT:         artifacts/phase3_5/safety_validation.json
METRIC:           safety_abort_rate, rollback_success_rate
CURRENT_STATUS:   PARTIALLY_SUPPORTED  (registry)
CORRECT_STATUS:   PARTIALLY_SUPPORTED  ✓ (registry is correct — but requires clarification)
EVIDENCE_CATEGORY: Mixed — Category A (6 hard stops via live_safety_results.json) +
                           Category B (2 hard stops dry-run only)

CRITICAL MISCLASSIFICATION RISK:
  The registry says "6/8 hard stops validated in dry-run (Category B)" but
  PHASE4_EVIDENCE_RECONCILIATION.md (Category A table) lists:
    "Safety 8/8 hard stops → artifacts/phase4/safety/live_safety_results.json → PASS"
  This is a DIRECT CONFLICT. The registry says 6/8 Category B; the reconciliation
  document says 8/8 Category A (live).

  Resolution required: If live_safety_results.json genuinely shows 8/8 hard stops
  on real Linux tc infrastructure (Category A), the registry should be updated to
  reflect SUPPORTED for the infrastructure-validated hard stops. However, 2 hard stops
  (rollback_failure and cascade_failure) specifically require live error-rate measurements
  during a real RIFT attribution run (Category C precondition). Until Category C evidence
  exists, those 2 remain at best Category A (infrastructure confirmed) not SUPPORTED.

  The claim "all 8 safety hard stops" cannot be asserted as fully validated until all
  8 are tested in the context of a live RIFT attribution run.

LIMITATION_L1:    Rollback_failure hard stop requires live tc environment (Category A confirmed)
LIMITATION_L2:    Cascade_failure hard stop requires live error rate measurement
CLASSIFICATION:   SUPPORTED_WITH_SCOPE for 6/8; PLANNED for 2/8 requiring live RIFT run
  → In paper: "6/8 safety hard stops validated (Category A/B). 2/8 (rollback_failure,
    cascade_failure) require live RIFT attribution run for full validation (Category C)."

NOTES:
  - The claim text says "all 8" — this overstates current evidence and must be scoped.
  - EXP-008 status is DRY_RUN_READY (not READY_FOR_LINUX), which is inconsistent
    with Category A evidence already existing in live_safety_results.json. This
    status should be updated to reflect what was actually validated on Linux.
```

---

### C009

```
CLAIM_ID:         C009
CLAIM:            "RIFT can run reproducibly with the same seed producing identical results."
RQ:               null
EXPERIMENT:       EXP-010
ARTIFACT:         artifacts/phase3_5/reproducibility_checklist.json
METRIC:           result_hash_consistency
CURRENT_STATUS:   PARTIALLY_SUPPORTED  (registry)
CORRECT_STATUS:   PARTIALLY_SUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: B (synthetic reproducibility — MockTelemetry, Category B per reconciliation doc)
LIMITATION_L1:    Reproducibility depends on causal-learn version and OS
LIMITATION_L2:    Live execution introduces timing non-determinism in timestamps
LIMITATION_L3:    Synthetic reproducibility only (Category B)
CLASSIFICATION:   SUPPORTED_WITH_SCOPE
  → In paper: "Reproducibility validated on synthetic runs (same seed, same MockTelemetry
    input → identical result hash, Category B). Live reproducibility is subject to
    timing non-determinism from real telemetry ingestion."

NOTES:
  - PHASE4_EVIDENCE_RECONCILIATION.md confirms a Phase 4 repeatability artifact:
    artifacts/phase4/repeatability/repeatability_NL01.json — this is Category B
    (synthetic_substitution=True). Consistent with PARTIALLY_SUPPORTED.
  - EXP-010 status DRY_RUN_READY is correct.
  - Limitation L2 (timing non-determinism) is important for paper: timestamp-based
    metrics like EBD breakpoint t* will not be hash-identical across live runs.
```

---

### C010

```
CLAIM_ID:         C010
CLAIM:            "RIFT raw Precision@1 = 50%, Conditional Precision@1 = 60% on development set."
RQ:               RQ1
EXPERIMENT:       null  (these are pre-experiment frozen historical values)
ARTIFACT:         artifacts/phase3_5/v1_decomposition.json  (FROZEN — do not modify)
METRIC:           raw_precision_at_1=0.50, conditional_precision_at_1=0.60
CURRENT_STATUS:   PARTIALLY_SUPPORTED  (registry)
CORRECT_STATUS:   MISCLASSIFIED — should be PLANNED/SYNTHETIC_ONLY

MISCLASSIFICATION ANALYSIS:
  "PARTIALLY_SUPPORTED" implies these values have some partial live evidential basis.
  They do not. They are 100% Category B (MockTelemetry, synthetic faults, development set).
  A more precise classification would be "FROZEN_SYNTHETIC" or "HISTORICAL_BASELINE."
  The registry's own notes say: "FROZEN HISTORICAL EVIDENCE from Phase 3.5. Do NOT update
  these values." This is inconsistent with calling the claim PARTIALLY_SUPPORTED — the
  values cannot be "partially supported" toward any live accuracy claim; they are simply
  a pre-validation snapshot. Classifying them PARTIALLY_SUPPORTED risks being read as
  "50% P@1 is partially established as the live system's performance," which is false.

EVIDENCE_CATEGORY: B — SYNTHETIC ONLY (Category B per PHASE4_EVIDENCE_RECONCILIATION.md)
LIMITATION_L1:    SYNTHETIC BENCHMARK ONLY — Category B evidence
LIMITATION_L2:    Development set (36 scenarios), MockTelemetry
LIMITATION_L3:    FROZEN HISTORICAL EVIDENCE — not final publication results
LIMITATION_L4:    MUST NEVER be presented as live system performance
CLASSIFICATION:   PLANNED (frozen synthetic baseline — not a paper result)

ABSOLUTE RULE 5 VIOLATION RISK:
  These values (P@1=50%, Conditional=60%) MUST be labeled "SYNTHETIC ONLY" in every
  context. The reconciliation document is explicit: "Any paper that presents these as
  live results is committing scientific error." Any paper table, figure, or claim that
  cites these values without the full context label violates this rule.

NOTES:
  - These values are FROZEN and must never be modified in the artifact.
  - In paper: permissible citation only as:
    "Synthetic pre-validation baseline: raw P@1=50%, conditional P@1=60%
    (36 scenarios, MockTelemetry, Category B, Phase 3.5). Final results will come
    from held-out test set after Linux E2E."
  - The artifact path (v1_decomposition.json) is also referenced by C003 for
    correct_abstention_rate — these are separate metrics from the same frozen artifact.
  - No experiment ID is associated with C010 in the registry. This is correct — these
    values predate the formal experiment registry and should not be assigned to any
    numbered experiment to avoid confusion with live results.
```

---

### C011

```
CLAIM_ID:         C011
CLAIM:            "tc/netem works correctly for per-destination latency injection on Linux."
RQ:               null
EXPERIMENT:       null  (infrastructure validation, not a numbered experiment)
ARTIFACT:         artifacts/phase4/intervention/net1_latency.json
                  artifacts/phase4/intervention/net2_packet_loss.json
                  artifacts/phase4/intervention/net3_rollback.json
                  artifacts/phase4/intervention/net5_destination_isolation.json
METRIC:           tc_netem_200ms_verified, per_destination_isolation_confirmed
CURRENT_STATUS:   SUPPORTED  (registry)
CORRECT_STATUS:   SUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: A — Linux infrastructure evidence (real execution on manas1.fyre.ibm.com,
                   RHEL 9.6, kernel 5.14.0)
LIMITATION_L1:    tc band bug (handle '10:' → '1:10') fixed in Phase 4.5 (T3)
LIMITATION_L2:    Per-destination netem verified on Linux kernel 5.14
LIMITATION_L3:    Reproducible only on Linux with CAP_NET_ADMIN
CLASSIFICATION:   SUPPORTED — may appear in paper as infrastructure claim

NOTES:
  - This is correctly SUPPORTED by Category A evidence. The claim is scoped to
    infrastructure behavior (tc/netem) not to RIFT's attribution accuracy.
  - Limitation L1 (T3 fix) is important: the tc band fix is "IMPLEMENTED/MAC_TESTED/
    READY_FOR_LINUX" but has NOT been re-validated on Linux post-fix. The Category A
    evidence for tc was collected BEFORE the T3 fix. This means the current Linux
    evidence reflects the pre-fix tc behavior. Post-fix Linux re-validation is required
    to confirm the fix doesn't introduce regression.
  - Paper must note: "tc/netem validated on Linux 5.14; CAP_NET_ADMIN required;
    not reproducible on macOS."
```

---

### C012

```
CLAIM_ID:         C012
CLAIM:            "Online Boutique infrastructure deploys successfully (14 containers healthy)."
RQ:               null
EXPERIMENT:       null  (infrastructure validation)
ARTIFACT:         artifacts/phase4/testbed/health.json
METRIC:           n_healthy_containers=14, frontend_http_200
CURRENT_STATUS:   SUPPORTED  (registry)
CORRECT_STATUS:   SUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: A — Linux infrastructure evidence (manas1.fyre.ibm.com, Docker 29.7.2,
                   RHEL 9.6, Phase 4 execution)
LIMITATION_L1:    Linux-only — not reproducible on Mac
LIMITATION_L2:    Phase 4 specific environment (Docker 29.7.2, RHEL 9.6)
CLASSIFICATION:   SUPPORTED — may appear in paper as infrastructure claim

NOTES:
  - Correctly SUPPORTED. PHASE4_EVIDENCE_RECONCILIATION.md confirms:
    "Online Boutique 14 containers healthy → PASS" and "Boutique traffic active → PASS."
  - Prometheus and Jaeger operational (Category A) also confirmed in the same document.
  - This claim establishes the testbed precondition for all future Category C experiments.
  - Scope: this claim does NOT imply that RIFT has ingested telemetry from those
    containers — that requires T1+T2 fixes and is Category C.
```

---

### C013

```
CLAIM_ID:         C013
CLAIM:            "RIFT operates on a live production-like microservice system."
RQ:               RQ1
EXPERIMENT:       null
ARTIFACT:         null
METRIC:           null
CURRENT_STATUS:   UNSUPPORTED  (registry)
CORRECT_STATUS:   UNSUPPORTED  ✓ (registry is correct)
EVIDENCE_CATEGORY: None — no evidence of any category supports this claim
LIMITATION_L1:    PrometheusClient.collect() stub prevented live telemetry ingestion (T1 fix)
LIMITATION_L2:    OTel Collector not wired (T2 fix)
LIMITATION_L3:    tc band bug blocked live interventions (T3 fix)
LIMITATION_L4:    No RIFTRunRecord with live_telemetry_used=True has been produced
CLASSIFICATION:   UNSUPPORTED — MUST NOT appear in paper at all

ABSOLUTE RULE 1 VIOLATION:
  This claim asserts "live operation." It requires Category C evidence
  (live_telemetry_used=True RIFTRunRecord). No such record exists.
  T1+T2+T3 fixes are implemented and MAC_TESTED but NOT deployed on Linux.
  Publishing this claim in any form is a direct violation of the absolute rules
  in CLAIMS_REGISTRY.yaml and PHASE4_EVIDENCE_RECONCILIATION.md.

UPGRADE PATH:
  Step 1: Deploy T1+T2+T3 fixes on Linux (manas1.fyre.ibm.com)
  Step 2: Run one full E2E RIFT attribution with live Online Boutique traffic
  Step 3: Confirm at least one RIFTRunRecord with live_telemetry_used=True
  Step 4: Upgrade C013 to PLANNED (registry note specifies this upgrade path)
  Step 5: After EXP-001 live run, upgrade to SUPPORTED

NOTES:
  - Registry correctly documents the upgrade path in the notes field.
  - Infrastructure (C011, C012) being SUPPORTED does NOT imply C013 is partially
    supported. The gap between "infrastructure running" and "RIFT processing live
    telemetry" is exactly the T1+T2+T3 blocker.
  - Do NOT conflate Category A evidence (C011, C012) with Category C evidence
    (C013) in any paper draft.
```

---

## Implied Claims Not in Registry

The following claims are implied by the experimental design documents but have
no explicit entry in `docs/CLAIMS_REGISTRY.yaml`. They require registration
or explicit exclusion before paper submission.

### IC-001 — H3: Closed-loop update improves multi-cause attribution
**Source:** `docs/hypotheses.md` H3, `experiments/REGISTRY.yaml` EXP-013  
**Implied claim:** "RIFT's closed-loop Bayesian posterior update provides better
attribution than one-shot intervention selection on multi-cause or ambiguous faults."  
**Current evidence:** None — EXP-013 is READY_FOR_LINUX; RIFT-ONE-SHOT baseline
is not yet implemented.  
**Risk:** H3 appears in the hypothesis table (hypotheses.md) and in RQ_EXPERIMENT_MAP.md
but has no C-prefixed claim in CLAIMS_REGISTRY.yaml. If the paper discusses the
closed-loop mechanism, it is implicitly asserting IC-001 without a registered claim.  
**Action required:** Register as C014 with status PLANNED, or explicitly mark it
as not a paper claim.

### IC-002 — Oracle upper bound reference
**Source:** `experiments/REGISTRY.yaml` EXP-012, `docs/research/RQ_EXPERIMENT_MAP.md`  
**Implied claim:** "RIFT's Precision@1 is bounded above by the oracle result on
the development set."  
**Current evidence:** EXP-012 DRY_RUN_READY — oracle can run on Mac in synthetic mode.  
**Risk:** Oracle results shown alongside RIFT results without a registered claim
or explicit "ORACLE UPPER BOUND — not a real baseline" label could be misread
as a comparative result. EXP-012 carries the correct label in REGISTRY.yaml but
this must propagate to all paper tables.  
**Action required:** Register as C015 with status PARTIALLY_SUPPORTED (Category B,
synthetic oracle) or confirm it is only a reference frame, not a claim.

### IC-003 — H3 prerequisite: RIFT-ONE-SHOT baseline does not exist
**Source:** `experiments/REGISTRY.yaml` EXP-013 notes, `docs/research/RQ_EXPERIMENT_MAP.md`  
**Implied gap:** EXP-013 and H3 require a RIFT-ONE-SHOT baseline that "is not an
implemented baseline yet — must be created before Linux."  
**Risk:** Any discussion of closed-loop benefits in the paper implies a comparison
baseline that does not yet exist. This is an implementation blocker, not merely
an evidence gap.  
**Action required:** Implement RIFT-ONE-SHOT in `src/rift/baselines/` before
Linux execution. Add implementation-complete gate to pre-Linux checklist.

### IC-004 — Benchmark modesty (69 scenarios, 36 dev)
**Source:** `experiments/REGISTRY.yaml` (n_scenarios=36 across all experiments),
`docs/PAPER_EVIDENCE_MATRIX.md` ("69 scenarios" not mentioned — PAPER_EVIDENCE_MATRIX
references 36 dev scenarios only)  
**Implied claim:** Results are generalizable beyond the 36-scenario development set.  
**Risk:** 36 scenarios is a modest benchmark for causal attribution claims. H1 requires
p<0.05 with Cliff's δ>0.20; with n=36, effect size needs to be moderate-to-large to
achieve significance. The paper must disclose benchmark modesty in the Threats to
Validity section.  
**Action required:** Disclose in Threats to Validity: "Primary evaluation uses 36
development scenarios from a single system (Online Boutique). Generalization claims
are limited pending held-out evaluation and cross-system validation (H5, Phase 11)."

### IC-005 — Single-system scope (Online Boutique only)
**Source:** `docs/hypotheses.md` H5 (requires Sock Shop as system B),
`docs/research/RQ_EXPERIMENT_MAP.md` (H5 DEFERRED Phase 11)  
**Implied claim:** H1–H4 results generalize to microservice systems broadly.  
**Risk:** All current experiments (EXP-001 through EXP-014) use Online Boutique as
the sole system. The paper must not present H1–H4 results as evidence of general
applicability. H5 is explicitly DEFERRED to Phase 11.  
**Action required:** Scope all H1–H4 claims to "Online Boutique testbed." Add
generalization limitation to Threats to Validity. Do not claim H5 until Sock Shop
(or equivalent) experiments are complete.

---

## Paper Disclosure Requirements

The following disclosures are **mandatory** before any public paper draft includes
the corresponding claims.

| Claim | Mandatory Disclosure Before Publication |
|---|---|
| C001 | Must state: "Live attribution not yet demonstrated. Results pending Linux E2E with live_telemetry_used=True." |
| C002 | Must state: "H2 Wilcoxon test not yet run. Conditional P@1 results are planned, not achieved. Power analysis: requires n≥48 confounded scenarios." |
| C003 | Must state: "Abstention validated on synthetic non-identifiable scenarios (MockTelemetry, Category B). Live validation pending." |
| C004 | Must state: "H4 TOST/Wilcoxon tests not yet run on real data. Cost efficiency is a design goal, not a demonstrated result." |
| C005 | Must state: "H1/H2 ablation not yet run. RIFT > RIFT-OBS delta is a hypothesis, not a demonstrated result. Core novelty claim is unconfirmed." |
| C006 | Must state: "Comparison is SIEVE-LIKE (methodological reimplementation). No claim about the original Sieve system. Results pending live Linux run." |
| C007 | Must state: "FCI-PAG approximation validated on synthetic ground-truth only (Category B). Faithfulness assumption untested on live traffic." |
| C008 | Must state: "6/8 safety hard stops validated on Linux infrastructure (Category A). 2/8 (rollback_failure, cascade_failure) require live RIFT attribution run for full validation." |
| C009 | Must state: "Reproducibility validated on synthetic runs only (Category B, MockTelemetry). Live timing non-determinism not yet characterized." |
| C010 | MUST include label: "SYNTHETIC ONLY — Category B — FROZEN HISTORICAL EVIDENCE. Raw P@1=50%, Conditional P@1=60% are pre-validation synthetic baseline values, NOT live results." These values must NEVER appear in primary comparison tables without this label. |
| C013 | MUST NOT appear in paper in any form until upgraded to PLANNED after T1+T2+T3 Linux deployment. |
| IC-001 | H3 closed-loop claim must not appear without implementing RIFT-ONE-SHOT baseline and registering the claim. |
| IC-004 | Threats to Validity must disclose: 36-scenario benchmark, single system (Online Boutique), modest scale. |
| IC-005 | Threats to Validity must disclose: H5 generalization deferred to Phase 11; H1–H4 scoped to Online Boutique. |

---

## Critical Risk Claims

P0 risks that could invalidate the paper or constitute scientific error if not
addressed before submission.

### P0-RISK-1: C013 published as live result
**Claim:** C013 (RIFT operates on live system)  
**Risk level:** P0 — INVALIDATES PAPER  
**Why:** No RIFTRunRecord with live_telemetry_used=True exists. Publishing this as
a result fabricates Category C evidence from Category B + Category A.  
**Mitigation:** Do not include C013 in any paper draft until T1+T2+T3 deployed on
Linux and a live E2E run is confirmed.

### P0-RISK-2: C010 values surfacing as live P@1 results
**Claim:** C010 (P@1=50%, Conditional=60%)  
**Risk level:** P0 — SCIENTIFIC ERROR  
**Why:** Presenting synthetic development-set accuracy as live system performance
misleads readers about RIFT's actual capability. PHASE4_EVIDENCE_RECONCILIATION.md
states this explicitly as a scientific error.  
**Mitigation:** Every citation of these values must carry the SYNTHETIC/FROZEN/CATEGORY-B
label. They may never appear in a primary results table without that label.

### P0-RISK-3: H1–H5 claimed as confirmed before live tests run
**Claims:** C002, C004, C005, C006 (and IC-001/H3)  
**Risk level:** P0 — INVALID STATISTICAL CLAIMS  
**Why:** Absolute Rule 4 prohibits asserting statistical significance without tests
running on real data. None of H1–H5 Wilcoxon/TOST tests have been executed.
Running them on synthetic data and reporting as hypothesis test results is a
Type I validity error (per RQ_EXPERIMENT_MAP.md).  
**Mitigation:** Do not report p-values, Wilcoxon statistics, TOST results, or
Cliff's δ values from any test that ran on MockTelemetry data.

### P0-RISK-4: "Sieve" vs "SIEVE-LIKE" label error in tables
**Claim:** C006  
**Risk level:** P0 — MISREPRESENTATION OF PRIOR WORK  
**Why:** Labeling the comparison as "Sieve" (without the -LIKE qualifier) implies
comparison against the original Sieve system (Bhatt et al.), which is false. The
comparison is a methodological reimplementation.  
**Mitigation:** All paper tables, figure captions, and result descriptions must use
"SIEVE-LIKE" and include a footnote: "Methodological reimplementation; not the
original Sieve codebase."

### P0-RISK-5: C008 "all 8 hard stops" claim without full Category C validation
**Claim:** C008  
**Risk level:** P1 — OVERSTATED CLAIM  
**Why:** Asserting "all 8 safety hard stops" implies complete validation. Two hard
stops (rollback_failure, cascade_failure) have not been tested during a live RIFT
attribution run. The Phase 4 Category A evidence (live_safety_results.json showing
8/8) requires clarification on whether those 2 hard stops were truly triggered
under live conditions or only under infrastructure-level testing.  
**Mitigation:** Scope the claim to "6/8 safety hard stops fully validated (Category A/B);
2/8 confirmed at infrastructure level, pending live RIFT attribution run."

### P0-RISK-6: n_scenarios=36 vs n_confounded_required=48 inconsistency for H2
**Claim:** C002  
**Risk level:** P1 — UNDERPOWERED TEST  
**Why:** EXP-002 requires n≥48 confounded scenarios for 80% power (documented in
both REGISTRY.yaml and RQ_EXPERIMENT_MAP.md) but the development set has n_scenarios=36.
If only 36 scenarios are available total, H2 cannot achieve the specified power level.
Running H2 at n<48 and reporting "statistically significant" results without disclosing
the power shortfall is a statistical reporting error.  
**Mitigation:** Before Linux execution, resolve the 36 vs 48 discrepancy.
If only 36 scenarios exist, update the power analysis and report achieved power in the paper.

---

## Artifact Path Inconsistencies (Non-Critical, Must Be Resolved)

| Location | Path Listed | Notes |
|---|---|---|
| C007 (CLAIMS_REGISTRY.yaml) | `artifacts/phase3/fci_validation.json` | Phase 4 reconciliation doc references `artifacts/phase4/oracle_vs_fci/comparison.json` |
| PAPER_EVIDENCE_MATRIX.md | `artifacts/phase3/oracle_vs_fci.json` | Different path from both above |
| C003/C010 share same artifact | `artifacts/phase3_5/v1_decomposition.json` | Correct — both metrics come from same frozen file |
| EXP-008 status | `DRY_RUN_READY` | Inconsistent with Category A safety evidence in live_safety_results.json |

---

## Status

```
PASS / BLOCKED: BLOCKED

Reason: No Category C evidence exists. C013 is UNSUPPORTED. All core
performance claims (C001, C002, C004, C005, C006) are PLANNED. H1–H5
statistical tests have not been run on real data. The paper MUST NOT be
submitted in current state.

Blocking conditions (must ALL be cleared before paper submission):
  B1: T1+T2+T3 fixes deployed on Linux manas1.fyre.ibm.com
  B2: At least one RIFTRunRecord with live_telemetry_used=True produced
  B3: EXP-001 through EXP-007 run on live Online Boutique traffic
  B4: H1–H5 confirmatory tests (Wilcoxon/TOST) run on Category C data
  B5: Held-out evaluation completed (Phase 5 authorization)
  B6: RIFT-ONE-SHOT baseline implemented (prerequisite for EXP-013/H3)
  B7: n_scenarios vs n_confounded_required discrepancy resolved for EXP-002/H2
  B8: Artifact path inconsistencies for C007/FCI resolved across all documents

Non-blocking issues (must be addressed before final submission):
  NB1: C010 registry status should be reclassified from PARTIALLY_SUPPORTED
       to FROZEN_SYNTHETIC or PLANNED to prevent scope inflation
  NB2: C008 claim text "all 8" should be scoped to "6/8 fully validated; 2/8
       infrastructure-confirmed pending live RIFT run"
  NB3: C006 SIEVE-LIKE labeling must be enforced in all paper drafts
  NB4: IC-001 (H3) must be registered as C014 or explicitly excluded
  NB5: Threats to Validity section must disclose IC-004 (benchmark modesty)
       and IC-005 (single-system scope)
  NB6: RQ mapping inconsistency for C007 (RQ3 in registry vs RQ1 in
       PAPER_EVIDENCE_MATRIX.md) must be reconciled
```
