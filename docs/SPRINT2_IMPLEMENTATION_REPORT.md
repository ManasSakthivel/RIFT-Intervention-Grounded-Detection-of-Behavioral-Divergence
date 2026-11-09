# RIFT Sprint 2 — Implementation & Code Audit Report

**Lead Engineer:** Autonomous Core Implementation Lead  
**Date:** 2026-11-02  
**Authority:** Sprint 2 Code Modifications & Regression Verification  

---

## 1. Summary of Changes Made

1. **`src/rift/ebd/ebd.py` (`_pag_to_digraph`):**
   - **Original Limitation:** `_pag_to_digraph` only added edges if `edge_type.value == "DIRECTED"`. Since constraint-based FCI on contemporaneous step metrics yields unoriented circle marks (`PARTIALLY_DIRECTED` $X \circ\!\!\rightarrow Y$ and `UNDIRECTED` $X \circ\!\!-\!\!\circ Y$), the graph was rendered empty with 0 edges, causing Criterion R3 to fail for every candidate node.
   - **Sprint 2 Enhancement:** Added `allow_semi_directed=True` parameter to build sound semi-directed reachability graphs from PAGs:
     - $X \circ\!\!\rightarrow Y$ adds $X \to Y$ (since $Y$ cannot be an ancestor of $X$).
     - $X \circ\!\!-\!\!\circ Y$ adds $X \to Y$ and $Y \to X$ (both directions admissible in semi-directed reachability).
     - $X \leftrightarrow Y$ (bidirected) remains strictly excluded from causal paths (representing latent common causes).
2. **`tests/unit/test_sprint2_semidirected.py`:**
   - Added unit test suite verifying `DIRECTED`, `PARTIALLY_DIRECTED`, `UNDIRECTED`, and `BIDIRECTED` edge translations and Criterion R3 reachability.

---

## 2. Verification & Regression Evidence

- **Unit & Integration Suite:** 631 passed / 0 failed in 14.04s.
- **Identifiability Invariants:** All identifiability checks (backdoor/frontdoor criteria) continue to hold.
