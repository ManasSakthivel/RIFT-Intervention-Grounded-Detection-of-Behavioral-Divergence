# Sprint 4.4.0 — Causal Directionality: What Each Kind of Evidence Lets RIFT Conclude

Scope: offline, synthetic, dev and val only. Implementation: `src/rift/attribution_v3/pag_semantics.py` (graph hierarchy) and
`src/rift/attribution_v3/rift_v3.py` (how evidence is combined). Numbers: `analysis.json: <split>.directionality`.

## 1. Definitions and what each licenses

Notation: edge marks are read at each endpoint (`-` tail, `>` arrowhead, `o` circle = undetermined). "x ⇒ y" is any path along which no
hop carries an arrowhead at its tail-side end ("semi-directed").

| concept | operational definition in RIFT | what the system may conclude | what it may **not** conclude |
|---|---|---|---|
| **Directed ancestry** (`DIRECTED_ANCESTOR`) | a path x → … → y in which every hop is fully oriented tail→arrowhead in the PAG | Under FCI's assumptions (faithfulness, no selection bias, correct CI tests) x is an ancestor of y in every graph of the equivalence class | That the assumptions hold; that the path is the *only* connection; that x is a *root* |
| **Possible ancestry** (`POSSIBLE_ANCESTOR`) | at least one semi-directed path x ⇒ y exists (circles allowed) | x is *not excluded* as an ancestor of y | That x *is* an ancestor. `o-o` is symmetric, so the relation usually holds in both directions |
| **Semi-directed connectivity** (graph reachability in V2's `_pag_to_digraph`) | any path with edges traversable under V2's conventions, **including** `UNDIRECTED` edges in both directions and bidirected edges | Two services are statistically linked | Any direction, any ancestry. Treating it as ancestry is the "SEMI_DIRECTED_MISTAKEN_FOR_EVIDENCE" failure |
| **Undirected / circle-marked relationship** | `o-o`, `o--`, `---` | A dependence exists after conditioning on the tested sets | Which end is the cause |
| **Bidirected** (`SEMI_DIRECTED_CONNECTION` in the hierarchy) | `x <-> y` | Association not explained by either causing the other; a latent common cause or selection is suggested | That either service is a cause of the other |
| **Observational association** (`OBSERVATIONAL_ASSOCIATION` / correlation, EBD co-divergence) | EBD R1 divergence of two services, or a connected-but-unoriented PAG pair | The two series moved | Anything about cause, direction or order of cause |
| **Intervention-supported evidence** | a do() on x on one 30 s window yielding a CID-significant (Holm-corrected) shift in y relative to the pre-intervention window, with the positive control on x passing | An effect of the intervention (or of whatever else changed in that window) is detectable on y; with the CID grade of CANDIDATE it is *intervention-consistent* evidence | That x is a root; that no drift contributed (see CID doc); anything about services not intervened on |

The hierarchy is ordered `DIRECTED_ANCESTOR > POSSIBLE_ANCESTOR > SEMI_DIRECTED_CONNECTION > OBSERVATIONAL_ASSOCIATION > NO_SUPPORTED_RELATIONSHIP`.
**No class is ever upgraded**: a relation gets the strongest class its marks justify. Interventional evidence is a separate axis in the V3
output (`evidence_type`, `path_kind`, `cid_grades`) and is never encoded in the graph class.

## 2. How the old pipeline blurred these

1. V2's `_pag_to_digraph` adds both directions for `UNDIRECTED` edges and treats `PARTIALLY_DIRECTED`/bidirected as reachable, so "reachable" meant
   "connected". With defect D1 (see FCI doc) a `X o-> Z` collider edge was misreported as undirected, further widening reachability.
2. R3 (V2's candidate rule) required such reachability to another diverging service, so a *consequence* of being connected to a diverging
   service qualified a service as a candidate; V2 reports `path_kind = SEMI_DIRECTED` for all its wrong answers (27/27).
3. V2's confidence was a fixed constant per path kind (0.95 / 0.80), i.e. independent of the amount of evidence.

## 3. Measured informativeness of the learned PAG

Over all ordered observed pairs (x, y), by the PAG class of x ⇒ y, versus the simulator's true ancestor relation (full DAG with hidden nodes):

| class | dev: ancestor / not | precision as ancestor | val: ancestor / not | precision |
|---|---|---:|---|---:|
| DIRECTED_ANCESTOR | 0 / 1 | 0.00 | 2 / 0 | 1.00 |
| POSSIBLE_ANCESTOR | 291 / 540 | 0.350 | 199 / 345 | 0.366 |
| SEMI_DIRECTED_CONNECTION | 11 / 23 | 0.324 | 21 / 47 | 0.309 |
| OBSERVATIONAL_ASSOCIATION | 8 / 24 | 0.250 | 15 / 27 | 0.357 |
| NO_SUPPORTED_RELATIONSHIP | 275 / 769 | 0.263 | 278 / 692 | 0.287 |

* All-pairs base rate of true ancestry: 585/1942 = 0.30 (dev), 515/1626 = 0.32 (val). POSSIBLE_ANCESTOR is only a few points above this.
* Of connected pairs, **92.6% (dev; 400/432, Wilson 90–95)** and **85.7% (val; 252/294, 81–89)** are POSSIBLE_ANCESTOR in *both* directions — i.e.
  carry no direction information.
* For the 14 dev and 13 val V2 wrong roots, the PAG relation between the true root and the named service was `POSSIBLE_ANCESTOR` both ways (4
  dev, 6 val), `NO_SUPPORTED_RELATIONSHIP` both ways (9 dev, 7 val), or `SEMI_DIRECTED_CONNECTION` both ways (1 dev). In none did the graph indicate the root as the upstream end.

Interpretation: on these data, semi-directed reachability is **not** an ancestry indicator: it is nearly symmetric where it exists and is
absent for roughly half of true ancestor pairs (NO_SUPPORTED_RELATIONSHIP holds 275 of 585 = 47% of true ancestor pairs on dev and 278 of 515 = 54% on val;
these include indirect ancestors that are not adjacent in the skeleton, and pairs lost to missing PAGs). Overstating it as ancestry produces wrong roots, as the failure analysis shows.

## 4. Why a downstream service can be a genuine manifestation without being the root

A downstream service y of a root r can, truthfully:
* diverge (EBD R1 holds) with a **larger** anomaly than r (6/14 dev and 9/13 val V2 wrong roots; amplification such as retries or queue build-up
  adds to, rather than merely copies, the upstream disturbance);
* have **confirmed effects** on its own descendants (do() on y really does change them) — this is *true* and is exactly why V2 named it;
* have **no confirmed effect from r** if r was never intervened on (isolated by FCI, never a candidate), so nothing in the evidence contradicts y.

All three are consistent with y being a genuine *manifestation*, an intermediate cause (mediator) in the cascade, and not the *origin*. "Root" is a
claim about the **most upstream** controllable cause, which requires evidence that no other observed service explains y — in particular that
nothing upstream is itself intervention-supported as a cause of y. V3 therefore requires: (i) no confirmed effect *into* the named source from any
service that was intervened on, and (ii) no unresolved earlier divergence; and it records `MULTIPLE_INTERVENTIONAL_SOURCES`,
`UNRESOLVED_DIVERGENCE` or `PAG_CONTRADICTS_INTERVENTION` as caveats. A mediator whose upstream cause was never examined **cannot** be told apart
from a root by any of this evidence — the identifiability boundary (the adversarial A12 set, 7/7 unsafe for V3).

## 5. How V3 keeps these categories apart (and the limits of that)

* **Graph evidence never confers root status.** `test_graph_not_used_as_causal_evidence` supplies a reversed oracle PAG and asserts that the named root is
  unchanged while `PAG_CONTRADICTS_INTERVENTION` appears; V3 answers are produced from the intervention table only.
* **Observational evidence only nominates.** R1 divergence (a service moved) selects *whom to intervene on*; it is never itself attribution evidence.
* **Interventional evidence is labelled with its grade.** `cid_grades` are all CANDIDATE (see CID doc); V3's `DEFINITIVE_ROOT` string means
  "no caveats were raised by the decision rule", not "definitive". It was wrong or unsafe 25 of 48 times (dev) and 12 of 22 (val).
* **`path_kind` among V3 answers:** dev 0 DIRECTED, 43 SEMI_DIRECTED, 24 NONE; val 0, 17, 9. No V3 answer rests on a fully directed path.
* **Confidence is ordinal only.** 1.0 / 0.5 / 0.25 / 0.1 rank outcomes; they are not probabilities.
* **Limit:** the contradiction check uses `OBSERVATIONAL_ASSOCIATION`/`SEMI_DIRECTED_CONNECTION` between a source and a confirmed outcome. With
  recall of 0.35–0.42, a missing PAG edge is common and must not be read as contradiction; V3 only flags the presence of an *opposing*
  relation, not the absence of a supporting one. Whether it is well calibrated has not been assessed (it fired on 3 of 67 dev and 1 of 26 val answers).

## 6. What can legitimately be said

* "The learned PAG is mostly unoriented; its semi-directed reachability is not a reliable indicator of ancestry on these synthetic data."
* "An intervention-consistent effect (CANDIDATE grade) from x to y was observed in the do() window."
* "x is an intervention-consistent source among the services we intervened on, and no other intervened service showed a confirmed effect on x."
* **Not**: "x causes y" (without the qualifier), "x is the root cause", "the graph shows x → y", "DEFINITIVE".
