# Sprint 4.4.0 — FCI / PAG Graph Quality

Scope: offline, synthetic, **dev and val only**. Truth = the simulator's direct-edge set restricted to observed services
(`diagnostics.py::graph_quality`; hidden nodes excluded from the skeleton score). Per-scenario rows: `artifacts/sprint4_4_0/graph_quality.csv`;
aggregates: `analysis.json: <split>.graph` and `<split>.directionality`. *Validated on synthetic ground-truth scenarios* only.

**Skeleton recovery and orientation are reported separately because they are different questions.** Adjacency asks "did FCI find that two
services are statistically related?"; orientation asks "did it say which one produces the other?". RIFT's attribution needs the second.

## 1. PAG availability

| | dev (180) | val (72) |
|---|---:|---:|
| PAG learned (OK) | 138 | 58 |
| no PAG produced, `NONE` (FCI not run or returned nothing; cause not broken down here) | 21 | 5 |
| FCI error, `ERR` (e.g. INSUFFICIENT_SAMPLES) | 21 | 9 |

All metrics below are micro-aggregated over scenarios with a PAG (138 / 58). Scenarios without a PAG contribute no edges (no recall credit).

## 2. Skeleton recovery (adjacency only)

| | dev | val |
|---|---:|---:|
| true observed direct edges scored | 382 | 251 |
| TP / FP / FN | 162 / 78 / 220 | 89 / 54 / 162 |
| precision | **0.675** | **0.622** |
| recall | **0.424** | **0.355** |
| F1 | 0.521 | 0.452 |
| SHD (skeleton: FP + FN, orientation excluded) | 298 | 216 |

Per-structure and per-family breakdowns are in `analysis.json: <split>.graph.breakdowns`. For example, `shared_dependency` on dev has
TP 16 / FP 21 / FN 47, while `linear_chain` has TP 17 / FP 7 / FN 17.

**Did we improve skeleton recovery?** No. This sprint did not change FCI (`fci_runner.py` is frozen; its alpha, test and sample use are
unchanged). The skeleton numbers describe the *existing* FCI behaviour; they are new measurements, not improvements. Roughly 6 in 10 true
edges are missed and 1 in 3–4 reported edges is spurious on these data. The failure analysis shows what that costs (isolated roots).

## 3. Orientation

| | dev | val |
|---|---:|---:|
| learned edges | 277 | 167 |
| circle-marked (at least one circle endpoint) | 271 (97.8%) | 162 (97.0%) |
| fully directed (`->` / `<-`) | 1 | 2 |
| bidirected `<->` | 1 | 3 |
| tail-tail `---` | 4 | 0 |
| orientation scored on true edges (TP edges) | 162 | 89 |
| **correct orientation** | **0** | **1** |
| wrong orientation | 6 | 8 |
| not oriented (circle at one/both ends) | 156 | 80 |

Edge-kind distribution (corrected decoder), dev: `o-o` 247, `o->` 14, `<-o` 9, `---` 4, `<-` 1, `<->` 1, `o--` 1. Val: `o-o` 138,
`<-o` 14, `o->` 10, `<->` 3, `<-` 2.

**Can FCI reliably orient edges here?** No. 97–98% of learned edges are circle-marked; only 1 (dev) and 2 (val) are fully directed; of the
true edges that FCI found and committed to a direction on, 0 of 6 (dev) and 1 of 9 (val) were oriented correctly. Both counts are tiny, but
we did not investigate *why*. Candidate explanations (limited sample size, a weak CI test, non-Gaussian or non-linear effects,
autocorrelation violating FCI's i.i.d. assumption) are untested hypotheses.

## 4. The endpoint-mark decoding defect (D1)

### 4.1 What the defect is
`src/rift/fci/fci_runner.py::_decode_pag_edges` (frozen, Sprint 4.3.0) documents causal-learn's matrix as
"`graph[i][j] = 2, graph[j][i] = -1` ⇒ `i o-> j`". causal-learn's convention is that `M[x][y]` is the endpoint mark **at x** of the edge
between x and y (-1 tail, 1 arrowhead, 2 circle). The decoder's fully directed branches (`(-1, 1)` ⇒ `i -> j`) follow that convention, but its
partially-directed branches do not: under the correct convention `(2, -1)` is a circle at i and a **tail** at j (`i o-- j`), whereas a true
`i o-> j` is `(2, 1)`. The pair `(2, 1)` (and its mirror `(1, 2)`) matches none of the decoder's branches and falls into the
`else: treat as UNDIRECTED` case. Two consequences: (a) every `o->` edge, including every collider edge FCI orients, is reported as `UNDIRECTED`
(the arrowhead is lost); (b) the rare `o--` edges (`(2, -1)`) are reported as `PARTIALLY_DIRECTED` (`o->`), i.e. an arrowhead is *invented*.
Dev has 23 `o->`/`<-o` edges and 1 `o--`; val has 24 `o->`/`<-o` and 0.

### 4.2 The collider test that demonstrates it
`tests/unit/test_sprint440_attribution_v3.py::test_mark_convention_matches_causal_learn_on_a_collider`:
data from `X -> Z <- Y` (X, Y independent standard normal, Z = X + Y + 0.5·noise, n = 800, seed 1). The collider is the one case in which FCI
*must* orient: an unshielded triple X–Z–Y with Z not in the separating set of (X, Y) yields arrowheads into Z. causal-learn returns
`M[X][Z] = 2`, `M[Z][X] = 1` (and likewise for Y). The test asserts that
1. the raw matrix has a circle at X and an **arrowhead at Z** (so the edge is `X o-> Z`: Z cannot be an ancestor of X);
2. the frozen decoder reports **both edges as `UNDIRECTED`** (the orientation information has been discarded);
3. the corrected decoder reports `xo->y` for both, classifies X→Z as POSSIBLE_ANCESTOR, and Z→X as not a possible ancestor;
4. the frozen reachability graph (`ebd._pag_to_digraph`, bidirectional for UNDIRECTED) **contains the edge Z→X** — i.e. the defect makes
   a collider's *effect* appear able to reach its *causes*. Empirically verified on seeds 1–3.

### 4.3 Why a V3-only decoder is necessary
The frozen decoder and the consumers of `PAGResult.edges` are part of the Sprint 4.3.0 freeze (`verify_freeze()` hashes 37 files; changing
`fci_runner.py` or `ebd.py` would invalidate the freeze and V2's published results). The correction therefore lives in the new
`src/rift/attribution_v3/pag_semantics.py::decode_marks` (reading the raw matrix) with `to_pag_result` re-encoding edges for any unmodified
code that needs a `PAGResult`. V2 is untouched and keeps the defect, which is part of what the V2-vs-V3 comparison measures.

### 4.4 How much did it matter?
Little for V2 in this corpus: with re-decoded marks V2's dev P1 stays at 28/68 and val moves from 8 to 7. This is expected because
97%+ of edges are `o-o`, which both decoders agree on. The defect matters when FCI *does* find a v-structure — exactly the evidence that
would be most informative — and it would matter more with better-powered data.

## 5. Root connectivity and isolation (dev vs val; learned vs oracle)

| | dev | val |
|---|---:|---:|
| true root instances (observed) | 71 | 35 |
| root diverges (EBD R1) | 68 | 35 |
| **root isolated in the learned PAG** (zero PAG neighbours) | **16** (14 of 57 ATTRIBUTE scenarios) | **7** (6 of 29) |
| root is a V2 candidate | 53 instances | 27 |
| root intervened on by V2 | 49 | 21 |
| root's effect confirmed by V2 | 33 | 13 |
| ATTRIBUTE scenarios with root in V2 candidate set | 43/57 = 75% (Wilson 63–85) | 23/29 = 79% (62–90) |
| ATTRIBUTE scenarios with no PAG at all | 11 | 2 |

**Oracle comparison** (`V2` run with the true observed-DAG supplied as a fully oriented PAG; privileged, never used for any claim):

| | learned | oracle graph | V3 (learned) |
|---|---:|---:|---:|
| dev P1 | 28/68 | 39/68 | 32/68 |
| val P1 | 8/31 | 19/31 | 13/31 |
| dev unsafe | 52 | 51 | 35 |
| val unsafe | 27 | 22 | 13 |

An oracle graph helps V2's accuracy substantially (+11 correct on each split) but does **not** reduce V2's unsafe answers much (52→51, 27→22)
— so graph errors are not the main cause of unsafe answers; abstention logic and CID evidence are. V3 recovers 4 of the 11 (dev) and 5 of the
11 (val) additional correct answers that an oracle graph gives V2, without using the graph for candidate selection, and cuts unsafe answers more
than the oracle graph does. V3 still sits below the oracle-graph P1.

## 6. Directed, possible and associational relations (what the PAG lets us say)

(See `SPRINT4_4_0_CAUSAL_DIRECTIONALITY.md` for definitions.) Over all ordered observed pairs:

| PAG class of (x, y) | dev: x true ancestor of y / not | precision as ancestor | val: true / not | precision |
|---|---|---:|---|---:|
| DIRECTED_ANCESTOR | 0 / 1 | 0.00 | 2 / 0 | 1.00 |
| POSSIBLE_ANCESTOR | 291 / 540 | 0.35 | 199 / 345 | 0.37 |
| SEMI_DIRECTED_CONNECTION | 11 / 23 | 0.32 | 21 / 47 | 0.31 |
| OBSERVATIONAL_ASSOCIATION | 8 / 24 | 0.25 | 15 / 27 | 0.36 |
| NO_SUPPORTED_RELATIONSHIP | 275 / 769 | 0.26 | 278 / 692 | 0.29 |

The all-pairs base rate of ancestry is 0.30 (dev: 585 ancestor pairs of 1,942 ordered pairs) and 0.32 (val: 515 of 1,626), so even POSSIBLE_ANCESTOR is only marginally
above chance as an ancestry indicator. 92.6% (dev) and 85.7% (val) of connected pairs are POSSIBLE_ANCESTOR in **both** directions — carrying no
direction information at all. DIRECTED_ANCESTOR is too rare (1 pair dev, 2 val) to say anything about its precision.

## 7. What this sprint can and cannot say about the graph
* The learned PAG is a **noisy, sparse, almost-unoriented association graph** on these data (F1 0.45–0.52; 97% circle edges).
* It is useful, at best, as a diagnostic and for a *contradiction* check; V3 therefore never lets it select or confirm a root.
* We cannot claim that FCI "fails" in general — only that the frozen configuration, on these simulated telemetry windows, does not orient.
  Whether more data, a different CI test, or a time-series-aware algorithm would is untested.
* Orientation counts are very small (6 and 9 scored oriented edges); treat the accuracy figures as "no evidence of reliable orientation",
  not as an estimate of an error rate.
