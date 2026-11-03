# Sprint 4.4.0 — Root-Cause Attribution Failure Analysis

Scope: offline, synthetic, **dev (180) and val (72) only**; no held-out scenarios were opened, no live intervention was run. Results are
*validated on synthetic ground-truth scenarios* and *intervention-consistent* only in the simulator's sense. Ground truth is used for
post-hoc labelling (`src/rift/attribution_v3/diagnostics.py::trace_scenario`); no method sees it.

Sources: `artifacts/sprint4_4_0/failure_traces_{dev,val}.json` (180 / 72 per-scenario traces), `analysis.json`, `v3_{dev,val}.json`,
`cid_audit.json`. "V2" = frozen RIFT-FULL-V2 (config A1-FULL); "V3" = `src/rift/attribution_v3/rift_v3.py::run_v3`, V3-FULL.

## 1. How V2 chooses a root (so the failures are interpretable)

V2 (`rift_v2.py::run_v2`, frozen) (i) selects as candidates services that satisfy EBD R1 (divergence) and R3 (a PAG/semi-directed path
to another diverging service, with a leaf fallback), (ii) intervenes on candidates in MSIS-utility order, (iii) counts as outcomes only
diverging services reachable in `_pag_to_digraph`, (iv) confirms with CID (1000 permutations, Bonferroni), and (v) names the candidate with
the best confirmed-effect evidence. The graph therefore influences *which services are even tested* and *which effects can be seen*.

## 2. Outcome counts of V2

| | dev (n=180) | val (n=72) |
|---|---:|---:|
| ATTRIBUTE scenarios | 68 | 31 |
| correct root named (P1) | 28 | 8 |
| **wrong root named** | **14** | **13** |
| lost ATTRIBUTE (abstained or no answer) | 26 | 10 |
| unsafe on ABSTAIN_REQUIRED | 38 | 14 |
| correct abstention | 74 | 27 |

## 3. The 14 dev and 13 val wrong-root cases

**Finding W1 — every wrong root was a descendant of a true root.** 14/14 (dev) and 13/13 (val) named services are descendants of the true
root in the simulator DAG (`failure_summary.wrong_named_is_descendant_of_root`), and in all of them V2's evidence path kind was
`SEMI_DIRECTED` (`wrong_path_kind`). In none of the 27 did the PAG supply a directed path.

**Finding W2 — the signals V2 was meant to exploit did not discriminate.**
* The true root diverged *earlier* than the named service in 9/14 dev and 7/13 val cases.
* The true root had a *smaller* anomaly than the named service in 6/14 dev and 9/13 val cases (descendants accumulate/amplify anomalies).
* The learned PAG relation between root and named service was `POSSIBLE_ANCESTOR` in *both* directions (4 dev, 6 val) or
  `NO_SUPPORTED_RELATIONSHIP` (9 dev, 7 val; i.e. the root was not connected to the service V2 named), with 1 dev `SEMI_DIRECTED_CONNECTION`.
  Even where the root was connected, the PAG gave no direction (see `SPRINT4_4_0_CAUSAL_DIRECTIONALITY.md`).

**Finding W3 — causal chain of the failure (where did the true root get lost?)**

| step where the true root dropped out | dev (14) | val (13) |
|---|---:|---:|
| root diverges but is **isolated in the learned PAG** (no adjacent edge, so no R3 path, so never a candidate) | 8 | 5 |
| root never crosses the R1 divergence rule | 2 | 0 |
| root a candidate but **not intervened / explained away** | 2 | 2 |
| root intervened and its effects **confirmed** but another service was selected as the source | 1 | 3 |
| root intervened but its effect was **not confirmed** | 1 | 2 |
| root connected but **fails R3** | 0 | 1 |

(`failure_summary.wrong_root_chain`.) The single largest cause (8 of 14 dev, 5 of 13 val) is FCI isolating the root. When the root is not
a candidate, V2 can only choose among its descendants, and each descendant that has a confirmed effect on a further descendant looks
like a source. This is the mechanism by which "downstream stronger anomaly" and "semi-directed mistaken for evidence" appear together in
the category counts (SEMI_DIRECTED_MISTAKEN_FOR_EVIDENCE: 14 dev, 13 val).

**Finding W4 — this is correct reasoning from bad inputs, not a random error.** In the cases where the true root was never a candidate,
the named service often *does* have confirmed effects on real descendants; V2's source rule (no confirmed effect into it from another
intervened candidate) is satisfied simply because the real upstream node was never intervened on.

### Representative scenario-level traces

(All numbers are read from `failure_traces_*.json` and `v3_*.json`. `t*` = EBD onset; anomaly in sigma units.)

**V2D-0015 (dev, diamond / compound, delayed_downstream_effects).** True root `yarrow` (edges yarrow→juniper, yarrow→sage). `yarrow`
diverges at t* = 160 s (anomaly 18.3) — before `sage` (200), `poppy` (250), `juniper` (280), `lotus` (360) — but is **isolated in the PAG**
(it has no learned neighbour; the three learned edges are juniper–sage, lotus–poppy and poppy–sage). Candidates: sage, poppy, juniper, lotus (`yarrow` fails R3). V2
intervened on sage, poppy, juniper and confirmed `juniper→poppy` and `poppy→lotus`; it named **`juniper`**, a child of `yarrow`.
V3 treats every R1 service as a candidate, intervenes on `yarrow`, and names **yarrow (DEFINITIVE_ROOT, correct)**. The learned PAG
contributed nothing positive here.

**V2D-0021 (dev, diamond / cascading, delayed_propagation).** True root `yarrow` (→basil, →larch). It diverges at 150 s and is isolated in
the PAG. V2 intervened on basil, fjord, zinnia, larch, confirmed `larch→{fjord, zinnia}` and named **`larch`** (a child of `yarrow`). V3
intervenes on `yarrow` as well and reports `QUALIFIED_ROOT` (caveat `MULTIPLE_INTERVENTIONAL_SOURCES`: both yarrow and another service
look like sources); `yarrow` is top-ranked (confidence 0.5, ordinal) — correct, with an explicit caveat.

**V2D-0017 (dev, branching / latency_degradation, multiple_onsets).** True root `poppy` (→ivy, →quill). `poppy` **never crosses R1 on the
dev telemetry**; only `quill` and `ivy` diverge (both at t* = 230). V2 intervened on `ivy`, confirmed `ivy→quill` (an artifact: ivy is not an
ancestor of quill; both are children of poppy — a confounded pair) and named **`ivy`**. V3 returns
`POSSIBLE_ROOT` with reason `INTERVENTION_NOT_VERIFIED` (no confirmed effect after Holm correction; possible roots listed: quill, ivy) → no attribution
(abstention; counted as LOST_ATTRIBUTE, not unsafe). This is an **identifiability boundary**: the
true root is unobserved as a diverging series, so no observational or interventional test over the remaining services can recover it.

**V2V-0001 (val, confounding / retry_amplification, oscillation, low_magnitude).** True root `yarrow` (→aspen→basil→sorrel). All four
services diverge within 20 s. `yarrow` was a candidate, was intervened on, and **its effects on aspen and sorrel were confirmed**; but `basil`
was also intervened on and confirmed on aspen, sorrel *and yarrow* (the last is a spurious confirmation: basil is not an ancestor of yarrow).
V2 named **`basil`**; V3 also names **`basil`** (DEFINITIVE_ROOT, unsafe). The cid audit attributes 2 of the 3 confirmed effects from
`basil` to non-ancestral pairs affected by window drift (oscillation scenario). This is a **remaining V3 failure** caused by CID
evidence quality, not by the graph.

**V2V-0011 (val, multiple_upstream / resource_saturation, two true roots olive and pine).** Both roots were candidates, intervened on and
confirmed (olive→mint, pine→heath); V2 named **`quince`** (their common child, with the largest anomaly, 23.3). V3 returns
`QUALIFIED_ROOT [MULTIPLE_INTERVENTIONAL_SOURCES]` with `olive` first and `pine` second — a correct answer with an honest caveat that more
than one source exists.

## 4. Effect of FCI root isolation on V2

* Roots that diverge: dev 68 of 71, val 35 of 35. **Isolated in the learned PAG: 16 (dev), 7 (val)** — 14 of 57 dev ATTRIBUTE scenarios and
  6 of 29 on val contain at least one isolated root.
* Root in V2's candidate set: dev 43/57 (75%; Wilson 63–85), val 23/29 (79%; 62–90).
* ATTRIBUTE scenarios with **no PAG at all** (FCI failed or never ran): dev 11, val 2. In these V2 falls back to leaf/observational behaviour.
* V2 with the **oracle** graph reaches P1 = 39/68 (dev), 19/31 (val) versus 28/68 and 8/31 learned. That ~11 scenario gap on each split is
  an upper bound on what better *graph* learning could give V2, and it is **not** reached by V3 (32/68, 13/31).
* Re-decoding V2's PAG with the corrected mark convention (defect D1) alone changed V2's results very little (dev P1 unchanged at 28/68;
  val 8→7) — so the decoder defect is real but is not the main driver of the V2 failures. Root isolation and candidate filtering are.

## 5. How V3 changes the intervention strategy

| aspect | V2 (frozen) | V3 |
|---|---|---|
| candidates | R1 and R3 (graph-filtered, root can be excluded by isolation) | **all R1-divergent services** |
| outcomes of an intervention | services reachable in the (mis-decoded) PAG | **all other divergent services** (graph-agnostic) |
| controls | none | **positive control** on x itself (manipulation check) |
| multiplicity | Bonferroni | Holm |
| explained-away services | skipped | still intervened on, so mutual effects are visible |
| source rule | no confirmed effect *into* the source | same, but mutual effects leave no source ⇒ abstain |
| earlier divergence | not checked | unresolved earlier divergence blocks attribution |
| PAG role | selects candidates and outcomes | diagnostic + **contradiction caveat only** |
| decision labels | confidence constants 0.95 / 0.80 | DEFINITIVE / QUALIFIED / POSSIBLE / INSUFFICIENT / NON_IDENTIFIABLE; ordinal confidence |

Cost: mean interventions per scenario 2.51 (dev) and 3.19 (val) versus 1.49 and 1.71 for V2; mean experiment duration 75.3 s / 95.8 s versus
44.8 s / 51.3 s; runtime ~0.07–0.11 s vs ~0.03–0.04 s per scenario. (All simulated; real interventions would incur recovery time.)

## 6. Which categories V3 resolves and which remain

**Largely resolved (in the sense of fewer wrong/unsafe answers on dev and val):**

| failure | V2 | V3 |
|---|---:|---:|
| wrong-root answers, dev | 14 | 7 |
| wrong-root answers, val | 13 | 3 |
| unsafe, dev | 52 | 35 |
| unsafe, val | 27 | 13 |
| root isolated by FCI (8 dev / 5 val chain entries) | root excluded | root intervened on (it is a candidate when it diverges) |

P1 changes by candidate set: reverting V3 to R3 candidates (`V3-R3-CANDIDATES`) drops P1 to 24/68 (dev) and 8/31 (val) and raises wrong roots to 12 and 9,
so the candidate change accounts for most of the P1 gain. Removing the symmetry check (`V3-NO-SYMMETRY-CHECK`) costs safety (unsafe 54 vs 35 dev; 23 vs 13 val).
The manipulation check and earlier-divergence guard each add a smaller safety contribution (unsafe 36 / 16 without them).

**Remaining:**
* **Unobserved/never-diverging roots.** ROOT_UNOBSERVED ABSTAIN_REQUIRED scenarios still produce unsafe answers (dev 4, val 4) and the adversarial
  A12 set (7/7 unsafe). This is an identifiability boundary, not a tunable error.
* **Weak signal.** WEAK_SIGNAL ABSTAIN_REQUIRED unsafe answers: dev 13 (10 of them name a true root), val 5 (4). The answer is *right*
  in the sense that a true root is named, but the scenario was labelled "abstain required" because the evidence is statistically inadequate.
  These count as unsafe under the pre-registered definition.
* **Spurious CID confirmations** (drift and ordinary ~5% false positives) accounted for in 15 of V3's 35 dev unsafe answers and 4 of 13 val (see CID doc).
* **Co-faulted services / multiple roots** (`parallel_independent`, `overlapping_faults`): V2D-0022, V2D-0117, V2V-0003 — V3 names a service that is not a
  true root (a descendant of one, or a co-faulted service).

### Remaining V3 wrong-root scenarios (dev 7, val 3; all trace-derived)

| scenario | structure / temporal | true root(s) | V3 named (status) | spurious CID confirmations from named service |
|---|---|---|---|---|
| V2D-0022 | parallel_independent / intermittent | clover, thorn | olive (QUALIFIED) | 2 drift |
| V2D-0054 | shared_dependency / delayed | yarrow | kale (DEFINITIVE) | 1 clean FP |
| V2D-0059 | linear_chain / recovery_delay | ginger | yarrow (DEFINITIVE) | 1 clean FP |
| V2D-0117 | multiple_upstream / overlapping | thorn, wisteria | violet (QUALIFIED) | 1 clean FP (of 2 confirmed effects) |
| V2D-0126 | shared_dependency / multiple_onsets | basil | oak (QUALIFIED, UNRESOLVED_DIVERGENCE) | 1 clean FP |
| V2D-0146 | converging / oscillation | quill | basil (DEFINITIVE) | 2 drift |
| V2D-0162 | converging / recovery_delay | basil | sage (DEFINITIVE) | 1 clean FP |
| V2V-0001 | confounding / oscillation | yarrow | basil (DEFINITIVE) | 2 drift |
| V2V-0003 | converging / overlapping | sorrel, wisteria | umber (DEFINITIVE) | none flagged (descendant reached through a real confirmed path) |
| V2V-0071 | shared_dependency / oscillation | ivy | fjord (DEFINITIVE) | 4 drift |

(The audit's `n_nonancestral_confirmed` counts confirmed effects from the named service onto a non-ancestral outcome; "none flagged" means
every confirmed effect was a real ancestral relation, so the error is in *source selection*, not in a spurious test.) Six of the 7 dev
wrong roots and all 3 val wrong roots name a descendant of a true root (checked with `nx.has_path` on the true DAG). The exception is
V2D-0022 (`parallel_independent`, roots clover and thorn): `olive` is neither an ancestor nor a descendant of either root, i.e. an unrelated
service. In 9 of these 10 wrong-root scenarios the audit can see at least one spurious (non-ancestral) CID confirmation from the
named service (drift: V2D-0022, V2D-0146, V2V-0001, V2V-0071; ordinary clean false positive: V2D-0054, 0059, 0117, 0126, 0162);
V2V-0003 has none, so its error is source selection. That the spurious confirmation *caused* the wrong answer is not proven — it is a co-occurrence in the decision log.

## 7. Remaining unsafe answers and what the evidence supports

V3 dev unsafe = 35: 7 wrong roots + 28 on ABSTAIN_REQUIRED (WEAK_SIGNAL 13, NO_DISCRIMINATING_EVIDENCE 8, ROOT_UNOBSERVED 4, SYMMETRIC 2,
NO_FAULT 1). Val unsafe = 13: 3 wrong roots + 10 on ABSTAIN_REQUIRED (WEAK_SIGNAL 5, ROOT_UNOBSERVED 4, NO_DISCRIMINATING 1).
Of V3's dev unsafe answers, 25 had the DEFINITIVE status and 10 QUALIFIED; val 12 and 1. The status label is thus not a reliable safety signal.

Where the evidence only supports a hypothesis (not a mechanism): why a subset of WEAK_SIGNAL scenarios yield an answer even though the
effect is below the pre-registered adequacy level is likely a mix of chance significance (n=30, ~5% FP, ~50% power at 0.5 sigma) and drift;
we did not run an experiment that isolates the two.

## 8. Limits of this analysis
* One simulator and one generator for all splits; the 27 V2 wrong-root traces were analysed by structured counts plus the five hand-read traces above, not all individually.
* Categories in `failure_summary.categories_by_kind` are non-exclusive tags assigned by `diagnostics.py`.
* Dev was used both for failure discovery and to choose V3's components (symmetry check). Val was used only for confirmation, but
  val was also inspected for failure patterns (descriptive), so it is not an untouched test set. Held-out was not used.
